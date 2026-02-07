import QtQuick
import QtQuick.Window

Window {
    id: root
    property var b: (backend !== undefined && backend !== null) ? backend : null
    width: b ? b.width : 430
    height: b ? b.height : 150
    x: b ? b.posX : 0
    y: b ? b.posY : 0
    visible: false
    color: "transparent"
    flags: Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint | Qt.WindowDoesNotAcceptFocus

    property real slideOffset: 12

        Rectangle {
            id: card
            anchors.fill: parent
            radius: 10
            color: b ? b.backgroundColor : "#DD1C1C1C"
        border.color: "#2BFFFFFF"
        border.width: 1

        gradient: Gradient {
            GradientStop { position: 0.0; color: "#EE1C1C1C" }
            GradientStop { position: 1.0; color: "#D11C1C1C" }
        }

        opacity: 0.0
        y: slideOffset

        Behavior on opacity { NumberAnimation { duration: 140; easing.type: Easing.OutQuad } }
        Behavior on y { NumberAnimation { duration: 160; easing.type: Easing.OutCubic } }

            Row {
                id: content
                anchors.fill: parent
                anchors.margins: 16
                spacing: 16

            Column {
                id: volumeSection
                spacing: 10
                width: 140

                Row {
                    spacing: 10
                    Image {
                        width: 22
                        height: 22
                        source: (b && b.muted) ? Qt.resolvedUrl("../assets/icons/vol-muted.svg") :
                            ((b && b.volume > 60) ? Qt.resolvedUrl("../assets/icons/vol-high.svg") :
                            ((b && b.volume > 20) ? Qt.resolvedUrl("../assets/icons/vol-med.svg") : Qt.resolvedUrl("../assets/icons/vol-low.svg")))
                        fillMode: Image.PreserveAspectFit
                    }
                    Text {
                        text: (b && b.muted) ? "Mute" : ((b ? b.volume : 0) + "%")
                        color: b ? b.textColor : "#F2F2F2"
                        font.family: b ? b.fontFamily : "Noto Sans"
                        font.pointSize: 12
                        font.weight: Font.DemiBold
                        verticalAlignment: Text.AlignVCenter
                    }
                }

                Rectangle {
                    id: volumeBarBg
                    width: parent.width
                    height: 7
                    radius: 4
                    color: "#33FFFFFF"

                    Rectangle {
                        id: volumeBarFg
                        height: parent.height
                        radius: 4
                        color: b ? b.accentColor : "#00A4EF"
                        width: Math.max(6, Math.round(((b ? b.volume : 0) / 100) * (parent.width)))
                    }
                }

                Text {
                    text: b ? b.deviceLabel : "Default Output"
                    color: "#A8FFFFFF"
                    font.family: b ? b.fontFamily : "Noto Sans"
                    font.pointSize: 9
                    elide: Text.ElideRight
                    width: parent.width
                }
            }

            Rectangle {
                width: 1
                color: "#22FFFFFF"
                height: parent.height
            }

            Item {
                id: mediaSection
                visible: b ? b.showPlayer : true
                anchors.verticalCenter: parent.verticalCenter
                width: parent.width - volumeSection.width - 32
                height: parent.height

                Row {
                    spacing: 12
                    anchors.verticalCenter: parent.verticalCenter

                    Rectangle {
                        id: artFrame
                        width: 72
                        height: 72
                        radius: 8
                        color: "#22FFFFFF"
                        border.color: "#22FFFFFF"
                        border.width: 1

                        Image {
                            anchors.fill: parent
                            anchors.margins: 2
                            fillMode: Image.PreserveAspectCrop
                            source: b ? b.artUrl : ""
                            visible: b ? b.artUrl.length > 0 : false
                            cache: true
                            asynchronous: true
                        }

                        Image {
                            anchors.centerIn: parent
                            width: 26
                            height: 26
                            source: Qt.resolvedUrl("../assets/icons/play.svg")
                            visible: b ? b.artUrl.length == 0 : true
                            fillMode: Image.PreserveAspectFit
                        }
                    }

                    Column {
                        spacing: 4
                        width: 250

                        Text {
                            text: (b && b.trackTitle.length > 0) ? b.trackTitle : "No media"
                            color: b ? b.textColor : "#F2F2F2"
                            font.family: b ? b.fontFamily : "Noto Sans"
                            font.pointSize: 12
                            font.weight: Font.DemiBold
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Text {
                            text: b ? b.trackArtist : ""
                            color: "#B8FFFFFF"
                            font.family: b ? b.fontFamily : "Noto Sans"
                            font.pointSize: 10
                            elide: Text.ElideRight
                            width: parent.width
                        }

                        Row {
                            spacing: 8
                            Image {
                                width: 16
                                height: 16
                                source: (b && b.playing) ? Qt.resolvedUrl("../assets/icons/play.svg") : Qt.resolvedUrl("../assets/icons/pause.svg")
                                fillMode: Image.PreserveAspectFit
                            }
                            Text {
                                text: b ? b.playerName : ""
                                color: "#88FFFFFF"
                                font.family: b ? b.fontFamily : "Noto Sans"
                                font.pointSize: 9
                                elide: Text.ElideRight
                                width: 200
                            }
                        }

                        Row {
                            spacing: 10
                            Rectangle {
                                width: 24; height: 24; radius: 6; color: "#22FFFFFF"
                                Image { anchors.centerIn: parent; width: 16; height: 16; source: Qt.resolvedUrl("../assets/icons/prev.svg"); fillMode: Image.PreserveAspectFit }
                                MouseArea { anchors.fill: parent; onClicked: if (b) b.Previous() }
                            }
                            Rectangle {
                                width: 28; height: 28; radius: 8; color: "#33FFFFFF"
                                Image { anchors.centerIn: parent; width: 18; height: 18; source: (b && b.playing) ? Qt.resolvedUrl("../assets/icons/pause.svg") : Qt.resolvedUrl("../assets/icons/play.svg"); fillMode: Image.PreserveAspectFit }
                                MouseArea { anchors.fill: parent; onClicked: if (b) b.PlayPause() }
                            }
                            Rectangle {
                                width: 24; height: 24; radius: 6; color: "#22FFFFFF"
                                Image { anchors.centerIn: parent; width: 16; height: 16; source: Qt.resolvedUrl("../assets/icons/next.svg"); fillMode: Image.PreserveAspectFit }
                                MouseArea { anchors.fill: parent; onClicked: if (b) b.Next() }
                            }
                        }
                    }
                }
            }
        }
    }

    MouseArea {
        anchors.fill: parent
        hoverEnabled: true
        acceptedButtons: Qt.NoButton
        onEntered: if (b) b.HoverChanged(true)
        onExited: if (b) b.HoverChanged(false)
    }

    function animateShow() {
        card.opacity = 1.0
        card.y = 0
    }

    function animateHide() {
        card.opacity = 0.0
        card.y = slideOffset
    }

    Connections {
        target: b
        function onShowRequested() {
            root.visible = true
            animateShow()
        }
        function onHideRequested() {
            animateHide()
        }
    }

    onVisibleChanged: {
        if (visible) {
            animateShow()
        } else {
            animateHide()
        }
    }
}
