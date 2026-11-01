import QtQuick
import qs.Commons
import qs.Commons as Commons
import qs.Ui

BarWidget {
  id: root
  moduleName: "cody.barracuda-battery"
  readonly property string state: BatteryService.state
  readonly property int percentage: BatteryService.percentage
  readonly property bool charging: BatteryService.charging
  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  Commons.Translations { id: strings; directory: Qt.resolvedUrl("i18n") }

  WidgetButton {
    id: button
    bar: root.bar
    anchors.fill: parent
    labelVisible: false
    hasVisualContent: true
    fixedWidth: root.vertical ? -1 : content.implicitWidth + Style.space(16)
    tooltipText: root.state === "connected"
      ? strings.t(root.charging ? "charging" : "connected").arg(Commons.I18n.formatNumber(root.percentage))
      : strings.t(root.state)
    pressable: false
    interactive: true

    Row {
      id: content
      anchors.centerIn: parent
      spacing: Style.space(4)
      Text {
        textFormat: Text.PlainText
        text: "󰋋"
        font.family: Style.font.family
        font.pixelSize: Style.bar.iconFont
        color: root.percentage >= 0 && root.percentage <= 20 ? Commons.Color.urgent : button.foreground
        anchors.verticalCenter: parent.verticalCenter
      }
      Text {
        textFormat: Text.PlainText
        text: root.percentage >= 0 ? Commons.I18n.formatNumber(root.percentage) + "%" + (root.charging ? " ϟ" : "") : "—"
        font.family: Style.font.family
        font.pixelSize: Style.font.body
        color: root.percentage >= 0 && root.percentage <= 20 ? Commons.Color.urgent : button.foreground
        opacity: root.percentage >= 0 ? 1 : 0.55
        anchors.verticalCenter: parent.verticalCenter
      }
    }
  }
}
