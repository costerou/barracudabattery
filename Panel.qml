import QtQuick
import QtQuick.Layouts
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Commons as Commons
import qs.Ui

// Razer Barracuda X Chroma: battery in the bar, earcup colour in the panel. barracuda.py owns all device I/O; this file owns
// the chosen colour (saved in the bar entry's settings) and re-applies it whenever the headset (re)connects, because the
// headset falls back to its own lighting effect after a power cycle.
Panel {
  id: root
  moduleName: "cody.barracuda"
  ipcTarget: "cody.barracuda"

  readonly property string helper: Qt.resolvedUrl("barracuda.py").toString().replace(/^file:\/\//, "")
  readonly property var swatches: ["000000", "FF0000", "FF6A00", "FFD000", "00FF00", "00E5FF", "0040FF", "C000FF", "FF00A0", "FFFFFF"]
  readonly property string savedColor: normalizeHex(setting("color", ""))

  property bool present: false
  property bool connected: false
  property int battery: -1
  property bool charging: false
  property string lastError: ""
  property string pendingColor: ""
  property int swatchIndex: Math.max(0, swatches.indexOf(savedColor))
  property bool cursorActive: false

  readonly property color foreground: bar ? bar.foreground : Commons.Color.foreground
  readonly property color dim: Qt.darker(foreground, 1.55)
  readonly property string fontFamily: bar ? bar.fontFamily : Style.font.family
  readonly property string statusText: !present ? strings.t("notFound")
    : !connected ? strings.t("disconnected")
    : battery < 0 ? ""
    : strings.t(charging ? "charging" : "battery").arg(Commons.I18n.formatNumber(battery))

  function normalizeHex(value) {
    var s = String(value || "").replace(/^#/, "").toUpperCase()
    return /^[0-9A-F]{6}$/.test(s) ? s : ""
  }

  function refresh() {
    if (!statusProcess.running) statusProcess.running = true
  }

  function applyStatus(raw) {
    var s
    try { s = JSON.parse(raw) } catch (e) { lastError = "Bad status from barracuda.py"; return }  // i18n: ignore
    var wasConnected = connected
    present = s.present === true
    connected = s.connected === true
    battery = typeof s.battery === "number" && s.battery >= 0 && s.battery <= 100 ? s.battery : -1
    charging = s.charging === true
    lastError = ""
    if (connected && !wasConnected && savedColor !== "") sendColor(savedColor)
  }

  function chooseColor(hex) {
    hex = normalizeHex(hex)
    if (hex === "") return
    if (hex !== savedColor && bar && bar.shell) {
      root.settings = Object.assign({}, root.settings, { color: hex })
      bar.shell.updateEntryInline(root.moduleName, root.settings)
    }
    sendColor(hex)
  }

  // One write in flight; the latest pick wins once it finishes.
  function sendColor(hex) {
    if (colorProcess.running) { pendingColor = hex; return }
    colorProcess.command = ["python3", "-I", helper, "color", hex]
    colorProcess.running = true
  }

  function elide(text) {
    var v = String(text || "").replace(/\s+/g, " ").trim()
    return v.length > 140 ? v.substring(0, 137) + "…" : v
  }

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  onOpenedChanged: if (opened) {
    cursorActive = false
    refresh()
    Qt.callLater(function() { if (panel.loadedContent) panel.loadedContent.forceActiveFocus() })
  }

  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  Timer {
    interval: 60000
    repeat: true
    running: true
    triggeredOnStart: true
    onTriggered: root.refresh()
  }

  Process {
    id: statusProcess
    command: ["python3", "-I", root.helper, "status"]
    stdout: StdioCollector { id: statusOut; waitForEnd: true }
    stderr: StdioCollector { id: statusErr; waitForEnd: true }
    onExited: function(code) {
      if (code === 0) root.applyStatus(statusOut.text)
      else { root.lastError = root.elide(statusErr.text || "barracuda.py status failed"); root.connected = false }  // i18n: ignore
    }
  }

  Process {
    id: colorProcess
    stderr: StdioCollector { id: colorErr; waitForEnd: true }
    onExited: function(code) {
      root.lastError = code === 0 ? "" : root.elide(colorErr.text || "barracuda.py color failed")  // i18n: ignore
      if (root.pendingColor !== "") {
        var next = root.pendingColor
        root.pendingColor = ""
        root.sendColor(next)
      }
    }
  }

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰋋"
    opacity: root.connected ? 1 : 0.5
    labelText: root.connected && root.battery >= 0 && !vertical
      ? Commons.I18n.formatNumber(root.battery) + "%" + (root.charging ? "+" : "") : ""
    slotSize: Style.bar.iconSlot * (labelText !== "" ? 2 : 1)
    tooltipText: ""
    onPressed: function(b) {
      if (b === Qt.RightButton) root.refresh()
      else root.toggle()
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: panel.loadedContent
    contentWidth: panel.fittedContentWidth(Style.space(300))
    contentHeight: panel.fittedContentHeight(panel.loadedContentHeight, Style.space(400))

    content: PanelKeyCatcher {
      implicitHeight: column.implicitHeight
      anchors.fill: parent
      onMoveRequested: function(dx, dy) {
        if (!root.cursorActive) { root.cursorActive = true; return }
        var n = root.swatches.length
        root.swatchIndex = ((root.swatchIndex + dx + dy * 5) % n + n) % n
      }
      onActivateRequested: if (root.cursorActive) root.chooseColor(root.swatches[root.swatchIndex])
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        width: parent.width
        spacing: Style.space(12)

        PanelHero {
          width: parent.width
          title: strings.t("title")
          meta: root.statusText
          foreground: root.foreground
          fontFamily: root.fontFamily
          iconOpacity: root.connected ? 1 : 0.5
          iconComponent: Component {
            Text {
              textFormat: Text.PlainText
              text: "󰋋"
              color: root.foreground
              font.family: root.fontFamily
              font.pixelSize: Style.font.display
            }
          }
        }

        Text {
          textFormat: Text.PlainText
          visible: root.lastError !== ""
          width: parent.width
          text: root.lastError
          color: Commons.Color.urgent
          font.family: root.fontFamily
          font.pixelSize: Style.font.bodySmall
          wrapMode: Text.WordWrap
        }

        PanelSeparator { foreground: root.foreground }

        PanelSectionHeader {
          text: strings.t("lights")
          foreground: root.foreground
          fontFamily: root.fontFamily
        }

        Grid {
          id: grid
          columns: 5
          spacing: Style.space(8)
          readonly property real cell: (parent.width - spacing * (columns - 1)) / columns

          Repeater {
            model: root.swatches
            Rectangle {
              required property string modelData
              required property int index
              readonly property bool chosen: modelData === root.savedColor
              readonly property bool hot: mouse.containsMouse || (root.cursorActive && root.swatchIndex === index)
              width: grid.cell
              height: Style.space(32)
              radius: Style.cornerRadius
              color: "#" + modelData
              border.width: chosen || hot ? 2 : 1
              border.color: chosen ? Commons.Color.accent : hot ? root.foreground : root.dim
              Accessible.role: Accessible.Button
              Accessible.name: modelData === "000000" ? strings.t("off") : "#" + modelData

              Text {
                anchors.centerIn: parent
                visible: parent.modelData === "000000"
                textFormat: Text.PlainText
                text: strings.t("off")
                color: root.foreground
                font.family: root.fontFamily
                font.pixelSize: Style.font.caption
              }

              MouseArea {
                id: mouse
                anchors.fill: parent
                hoverEnabled: true
                cursorShape: Qt.PointingHandCursor
                onEntered: { root.cursorActive = true; root.swatchIndex = parent.index }
                onClicked: root.chooseColor(parent.modelData)
              }
            }
          }
        }

        RowLayout {
          width: parent.width
          spacing: Style.space(8)

          Rectangle {
            Layout.preferredWidth: Style.space(32)
            Layout.preferredHeight: Style.space(32)
            radius: Style.cornerRadius
            color: root.savedColor !== "" ? "#" + root.savedColor : "transparent"
            border.width: 1
            border.color: root.dim
          }

          TextField {
            Layout.fillWidth: true
            foreground: root.foreground
            placeholderText: strings.t("custom")
            text: root.savedColor !== "" ? "#" + root.savedColor : ""
            maximumLength: 7
            validator: RegularExpressionValidator { regularExpression: /#?[0-9A-Fa-f]{0,6}/ }
            onAccepted: root.chooseColor(text)
          }
        }
      }
    }
  }
}
