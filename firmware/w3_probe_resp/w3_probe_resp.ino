#include <WiFi.h>
#include <esp_wifi.h>
#include <Arduino.h>

#define SERIAL_BAUD       115200
#define HOP_INTERVAL_MS   200
#define REPORT_INTERVAL   8000
#define MAX_DEVICES       30
#define AUTO_RESPOND      false

typedef struct {
  uint8_t mac[6];
  char ssid[33];
  int32_t rssi;
  uint8_t channel;
  unsigned long lastSeen;
  uint16_t probeCount;
} DeviceEntry;

static DeviceEntry devices[MAX_DEVICES];
static int deviceCount = 0;
static int currentChannel = 1;
static unsigned long lastHop = 0;
static unsigned long lastReport = 0;
static unsigned long totalProbes = 0;
static unsigned long autoResponses = 0;

void printMac(const uint8_t* mac) {
  for (int i = 0; i < 6; i++) {
    if (mac[i] < 0x10) Serial.print("0");
    Serial.print(mac[i], HEX);
    if (i < 5) Serial.print(":");
  }
}

int findOrCreateDevice(const uint8_t* mac, const char* ssid, int32_t rssi, uint8_t ch) {
  for (int i = 0; i < deviceCount; i++) {
    if (memcmp(devices[i].mac, mac, 6) == 0) {
      devices[i].lastSeen = millis();
      devices[i].probeCount++;
      devices[i].rssi = rssi;
      devices[i].channel = ch;
      if (strlen(ssid) > 0 && strlen(devices[i].ssid) == 0) {
        strncpy(devices[i].ssid, ssid, 32);
        devices[i].ssid[32] = '\0';
      }
      return i;
    }
  }

  if (deviceCount < MAX_DEVICES) {
    memcpy(devices[deviceCount].mac, mac, 6);
    strncpy(devices[deviceCount].ssid, ssid, 32);
    devices[deviceCount].ssid[32] = '\0';
    devices[deviceCount].rssi = rssi;
    devices[deviceCount].channel = ch;
    devices[deviceCount].lastSeen = millis();
    devices[deviceCount].probeCount = 1;
    deviceCount++;
    return deviceCount - 1;
  }
  return -1;
}

void sendProbeResponse(const uint8_t* dstMac, const char* targetSsid) {
  uint8_t resp[50] = {0};

  resp[0] = 0x50;
  resp[1] = 0x00;

  memcpy(resp + 4, dstMac, 6);
  memcpy(resp + 10, "\xAA\xBB\xCC\xDD\xEE\xFF", 6);
  memcpy(resp + 16, "\xAA\xBB\xCC\xDD\xEE\xFF", 6);

  resp[22] = 0x00;
  resp[23] = 0x00;

  resp[24] = 0x01;
  resp[25] = 0x04;
  resp[26] = 0x82;
  resp[27] = 0x84;
  resp[28] = 0x8B;
  resp[29] = 0x96;

  resp[30] = 0x03;
  resp[31] = 0x01;
  resp[32] = (uint8_t)currentChannel;

  uint8_t ssidLen = strlen(targetSsid);
  if (ssidLen > 32) ssidLen = 32;
  resp[33] = 0x00;
  resp[34] = ssidLen;
  memcpy(resp + 35, targetSsid, ssidLen);

  int totalLen = 35 + ssidLen;

  esp_wifi_80211_tx(WIFI_IF_STA, resp, totalLen, false);
}

void probeSnifferCallback(void* buf, wifi_promiscuous_pkt_type_t type) {
  if (type != WIFI_PKT_MGMT) return;

  const wifi_promiscuous_pkt_t* pkt = (wifi_promiscuous_pkt_t*)buf;
  const uint8_t* payload = pkt->payload;
  uint16_t len = pkt->rx_ctrl.sig_len;

  if (len < 24) return;

  uint8_t frameType = payload[0] & 0x0C;
  uint8_t frameSubtype = payload[0] & 0xF0;

  if (frameType != 0x00 || frameSubtype != 0x40) return;

  totalProbes++;

  const uint8_t* srcMac = payload + 10;
  int32_t rssi = pkt->rx_ctrl.rssi;

  char ssid[33] = {0};
  uint8_t channel = pkt->rx_ctrl.channel;

  int pos = 24;
  while (pos < len - 2) {
    uint8_t eid = payload[pos];
    uint8_t elen = payload[pos + 1];

    if (eid == 0x00 && elen > 0 && elen <= 32) {
      memcpy(ssid, payload + pos + 2, elen);
      ssid[elen] = '\0';
      break;
    }
    pos += 2 + elen;
  }

  int idx = findOrCreateDevice(srcMac, ssid, rssi, channel);

  Serial.printf("\r\n[PROBE] src=");
  printMac(srcMac);
  if (strlen(ssid) > 0) {
    Serial.printf(" SSID=\"%s\"", ssid);
  } else {
    Serial.printf(" SSID=<wildcard>");
  }
  Serial.printf(" RSSI=%d CH=%d total=%lu\r\n", rssi, channel, totalProbes);

  if (AUTO_RESPOND && strlen(ssid) > 0) {
    sendProbeResponse(srcMac, ssid);
    autoResponses++;
    Serial.printf("  -> Auto-responded with probe response\r\n");
  }
}

void printReport() {
  Serial.println("\r\n+==============================================+");
  Serial.println("|     W3 Probe Responder - Device Report       |");
  Serial.println("+==============================================+");
  Serial.printf("| Total Probes:    %-27lu|\r\n", totalProbes);
  Serial.printf("| Tracked Devices: %-27d|\r\n", deviceCount);
  Serial.printf("| Auto Responses:  %-27lu|\r\n", autoResponses);
  Serial.printf("| Channel:         %-27d|\r\n", currentChannel);
  Serial.println("+----------------------------------------------+");
  Serial.println("| Device MAC          | RSSI | CH | Probes     |");
  Serial.println("+----------------------------------------------+");

  for (int i = 0; i < deviceCount; i++) {
    Serial.print("| ");
    printMac(devices[i].mac);
    Serial.printf(" | %4d | %2d | %5u     ", devices[i].rssi,
                  devices[i].channel, devices[i].probeCount);
    if (strlen(devices[i].ssid) > 0) {
      Serial.printf(" %s", devices[i].ssid);
    }
    Serial.println();
  }

  if (deviceCount == 0) {
    Serial.println("| (no devices tracked yet)                     |");
  }

  Serial.println("+----------------------------------------------+");
}

void setup() {
  Serial.begin(SERIAL_BAUD);
  delay(500);

  Serial.println("+----------------------------------------------+");
  Serial.println("|    W3 WiFi Probe Responder                   |");
  Serial.println("|    Board: ESP32-C6                           |");
  Serial.println("+----------------------------------------------+");

  WiFi.mode(WIFI_STA);
  WiFi.disconnect(true);
  delay(100);

  esp_wifi_set_promiscuous(true);
  esp_wifi_set_promiscuous_rx_cb(probeSnifferCallback);
  esp_wifi_set_channel(currentChannel, WIFI_SECOND_CHAN_NONE);

  Serial.printf("Promiscuous mode active on channel %d\r\n", currentChannel);
  Serial.printf("Auto-respond: %s\r\n", AUTO_RESPOND ? "ENABLED" : "DISABLED");

  lastReport = millis();
  lastHop = millis();
}

void loop() {
  unsigned long now = millis();

  if (now - lastHop >= HOP_INTERVAL_MS) {
    currentChannel++;
    if (currentChannel > 13) currentChannel = 1;
    esp_wifi_set_channel(currentChannel, WIFI_SECOND_CHAN_NONE);
    lastHop = now;
  }

  if (now - lastReport >= REPORT_INTERVAL) {
    printReport();
    lastReport = now;
  }

  delay(10);
}
