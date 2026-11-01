pragma Singleton
import QtQuick
import Quickshell
import Quickshell.Io

Singleton {
  id: root
  property string state: "waiting"
  property int percentage: -1
  property bool charging: false

  Process {
    id: listener
    command: ["python3", decodeURIComponent(Qt.resolvedUrl("battery.py").toString().replace(/^file:\/\//, "")), "--watch"]
    running: true
    stdout: SplitParser {
      onRead: function(line) {
        try {
          var data = JSON.parse(line)
          var valid = data.status === "connected" && Number.isInteger(data.percentage)
              && data.percentage >= 0 && data.percentage <= 100
          root.percentage = valid ? data.percentage : -1
          root.charging = valid && data.charging === true
          root.state = valid ? "connected" : (["waiting", "disconnected", "permission", "unavailable"].indexOf(data.status) >= 0 ? data.status : "unavailable")
        } catch (e) {
          root.percentage = -1
          root.charging = false
          root.state = "unavailable"
        }
      }
    }
    onExited: {
      root.state = "unavailable"
      root.percentage = -1
      root.charging = false
      restart.start()
    }
  }

  Timer { id: restart; interval: 3000; onTriggered: listener.running = true }
}
