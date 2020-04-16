import datetime
import logging
import os
import sys
import time
from collections import defaultdict
from random import randint
from threading import Timer, Condition
from yowsup.common import YowConstants
from yowsup.common.optionalmodules import (AxolotlOptionalModule,
                                           PILOptionalModule)
from yowsup.common.tools import Jid
from yowsup.layers import EventCallback, YowLayerEvent
from yowsup.layers.auth import YowAuthenticationProtocolLayer
from yowsup.layers.interface import ProtocolEntityCallback, YowInterfaceLayer
from yowsup.layers.network import YowNetworkLayer
from yowsup.layers.protocol_chatstate.protocolentities import OutgoingChatstateProtocolEntity, ChatstateProtocolEntity
from yowsup.layers.protocol_contacts.protocolentities import GetStatusesIqProtocolEntity, GetSyncIqProtocolEntity
from yowsup.layers.protocol_groups.protocolentities import ListGroupsIqProtocolEntity, LeaveGroupsIqProtocolEntity, \
    CreateGroupsIqProtocolEntity, AddParticipantsIqProtocolEntity, PromoteParticipantsIqProtocolEntity, \
    DemoteParticipantsIqProtocolEntity, RemoveParticipantsIqProtocolEntity, SubjectGroupsIqProtocolEntity, \
    InfoGroupsIqProtocolEntity
from yowsup.layers.protocol_ib.protocolentities import CleanIqProtocolEntity
from yowsup.layers.protocol_iq.protocolentities import PingIqProtocolEntity, PushIqProtocolEntity, \
    PropsIqProtocolEntity, CryptoIqProtocolEntity
from yowsup.layers.protocol_media.mediauploader import MediaUploader
from yowsup.layers.protocol_media.protocolentities import RequestUploadIqProtocolEntity, \
    ImageDownloadableMediaMessageProtocolEntity, AudioDownloadableMediaMessageProtocolEntity, \
    VideoDownloadableMediaMessageProtocolEntity
from yowsup.layers.protocol_messages.protocolentities import TextMessageProtocolEntity, BroadcastTextMessage
from yowsup.layers.protocol_presence.protocolentities import PresenceProtocolEntity, AvailablePresenceProtocolEntity, \
    UnavailablePresenceProtocolEntity, UnsubscribePresenceProtocolEntity, SubscribePresenceProtocolEntity, \
    LastseenIqProtocolEntity
from yowsup.layers.protocol_privacy.protocolentities import PrivacyListIqProtocolEntity
from yowsup.layers.protocol_profiles.protocolentities import SetStatusIqProtocolEntity, GetPictureIqProtocolEntity, \
    SetPictureIqProtocolEntity, GetPrivacyIqProtocolEntity, SetPrivacyIqProtocolEntity, UnregisterIqProtocolEntity

from .cli import Cli, clicmd

reload(sys)
sys.setdefaultencoding('utf8')

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)


class YowsupNewsbotLayer(Cli, YowInterfaceLayer):
    PROP_RECEIPT_AUTO = "org.openwhatsapp.yowsup.prop.cli.autoreceipt"
    PROP_RECEIPT_KEEPALIVE = "org.openwhatsapp.yowsup.prop.cli.keepalive"
    PROP_CONTACT_JID = "org.openwhatsapp.yowsup.prop.cli.contact.jid"
    EVENT_LOGIN = "org.openwhatsapp.yowsup.event.cli.login"
    EVENT_START = "org.openwhatsapp.yowsup.event.cli.start"
    EVENT_SENDANDEXIT = "org.openwhatsapp.yowsup.event.cli.sendandexit"

    MESSAGE_FORMAT = u"[{FROM}({TIME})]:[{MESSAGE_ID}]\t {MESSAGE}"

    FAIL_OPT_PILLOW = "No PIL library installed, try install pillow"
    FAIL_OPT_AXOLOTL = "axolotl is not installed, try install python-axolotl"

    DISCONNECT_ACTION_PROMPT = 0
    DISCONNECT_ACTION_EXIT = 1

    ACCOUNT_DEL_WARNINGS = 4

    def __init__(self, date, verbose=False):
        super(YowsupNewsbotLayer, self).__init__()
        YowInterfaceLayer.__init__(self)
        self.accountDelWarnings = 0
        self.connected = False
        self.username = "BotTom News"
        self.sendReceipts = True
        self.sendRead = True
        self.disconnectAction = self.__class__.DISCONNECT_ACTION_PROMPT
        self.credentials = None

        date = datetime.datetime.strptime(date, '%m.%d.%Y').date()
        # yesterday = date - datetime.timedelta(days=1)
        dayString = date.strftime("%m%d")
        # yesterdayString = yesterday.strftime("%m%d")
        videoExtension = '.mp4'
        videoFolderName = '/home/*****/yowsup/newsbot/video'
        videoFileName = 'Tagesschau100sArabic'
        videoFileNameToday = videoFileName + dayString + videoExtension
        # videoFileNameYesterday = videoFileName + yesterdayString + videoExtension
        videoFileTodayPath = videoFolderName + '/' + videoFileNameToday
        # videoFileYesterdayPath = videoFolderName + '/' + videoFileNameYesterday

        self.date = date
        self.videoFileTodayPath = videoFileTodayPath
        self.verbose = verbose

        self.messageQueue = []
        self.ackQueue = []
        self.messageTimer = None
        self.workingOff = False
        self.sendingMedia = False
        self.lock = Condition()

        self.jidAliases = {
            "*****": "************@s.whatsapp.net",
            "group": "***********-**********@g.us",
            "********": "************-**********@g.us",
        }

    def aliasToJid(self, calias):
        for alias, ajid in self.jidAliases.items():
            if calias.lower() == alias.lower():
                return Jid.normalize(ajid)

        return Jid.normalize(calias)

    def jidToAlias(self, jid):
        for alias, ajid in self.jidAliases.items():
            if ajid == jid:
                return alias
        return jid

    def setCredentials(self, username, password):
        self.getLayerInterface(YowAuthenticationProtocolLayer).setCredentials(
            username, password)

        return "%s@s.whatsapp.net" % username

    def sendNews(self):
        self.tryPrint("Send News")
        self.sendingMedia = True
        self.workingOff = True
        self.video_send(self.jidAliases["group"], self.videoFileTodayPath,
                        self.date.strftime("%d.%m.%y") + " - Nachrichten")
        self.message_send(
            self.jidAliases["group"],
            "Die Nachrichten vom " + self.date.strftime("%d.%m.%Y"))
        self.messageTimer = Timer(5.0, self.workOffMessageQueue, [])
        self.messageTimer.start()

    @EventCallback(EVENT_START)
    def onStart(self, layerEvent):
        self.L()
        return True

    @EventCallback(EVENT_SENDANDEXIT)
    def onSendAndExit(self, layerEvent):
        credentials = layerEvent.getArg("credentials")
        target = layerEvent.getArg("target")
        message = layerEvent.getArg("message")
        self.sendMessageAndDisconnect(credentials, target, message)
        return True

    @EventCallback(YowNetworkLayer.EVENT_STATE_DISCONNECTED)
    def onStateDisconnected(self, layerEvent):
        self.tryPrint("Disconnected: %s" % layerEvent.getArg("reason"))

        if self.disconnectAction == self.__class__.DISCONNECT_ACTION_PROMPT:
            self.connected = False
            sys.exit(0)
        else:
            os._exit(os.EX_OK)

    def assertConnected(self):
        if self.connected:
            return True
        else:
            self.tryPrint("Not connected")
            return False

################################## batch cmds ##################################

    def sendMessageAndDisconnect(self, credentials, jid, message):
        self.disconnectAction = self.__class__.DISCONNECT_ACTION_EXIT
        self.queueCmd("/login %s %s" % credentials)
        self.queueCmd("/message send %s \"%s\" wait" % (jid, message))
        self.queueCmd("/disconnect")
        self.startInput()

################################################################################

################################### presence ###################################

    @clicmd("Set presence name")
    def presence_name(self, name):
        if self.assertConnected():
            entity = PresenceProtocolEntity(name=name)
            self.toLower(entity)

    @clicmd("Set presence as available")
    def presence_available(self):
        if self.assertConnected():
            entity = AvailablePresenceProtocolEntity()
            self.toLower(entity)

    @clicmd("Set presence as unavailable")
    def presence_unavailable(self):
        if self.assertConnected():
            entity = UnavailablePresenceProtocolEntity()
            self.toLower(entity)

    @clicmd("Unsubscribe from contact's presence updates")
    def presence_unsubscribe(self, contact):
        if self.assertConnected():
            entity = UnsubscribePresenceProtocolEntity(
                self.aliasToJid(contact))
            self.toLower(entity)

    @clicmd("Subscribe to contact's presence updates")
    def presence_subscribe(self, contact):
        if self.assertConnected():
            entity = SubscribePresenceProtocolEntity(self.aliasToJid(contact))
            self.toLower(entity)

################################################################################

###################################### ib ######################################

    @clicmd("Send clean dirty")
    def ib_clean(self, dirtyType):
        if self.assertConnected():
            entity = CleanIqProtocolEntity("groups", YowConstants.DOMAIN)
            self.toLower(entity)

    @clicmd("Ping server")
    def ping(self):
        if self.assertConnected():
            entity = PingIqProtocolEntity(to=YowConstants.DOMAIN)
            self.toLower(entity)

################################################################################

############################## contacts/ profiles ##############################

    @clicmd("Set status text")
    def profile_setStatus(self, text):
        if self.assertConnected():

            def onSuccess(resultIqEntity, originalIqEntity):
                self.tryPrint("Status updated successfully")

            def onError(errorIqEntity, originalIqEntity):
                logger.error("Error updating status")

            entity = SetStatusIqProtocolEntity(text)
            self._sendIq(entity, onSuccess, onError)

    @clicmd("Get profile picture for contact")
    def contact_picture(self, jid):
        if self.assertConnected():
            entity = GetPictureIqProtocolEntity(
                self.aliasToJid(jid), preview=False)
            self._sendIq(entity, self.onGetContactPictureResult)

    @clicmd("Get profile picture preview for contact")
    def contact_picturePreview(self, jid):
        if self.assertConnected():
            entity = GetPictureIqProtocolEntity(
                self.aliasToJid(jid), preview=True)
            self._sendIq(entity, self.onGetContactPictureResult)

    @clicmd("Get lastseen for contact")
    def contact_lastseen(self, jid):
        if self.assertConnected():

            def onSuccess(resultIqEntity, originalIqEntity):
                self.tryPrint("%s lastseen %s seconds ago" % (
                    resultIqEntity.getFrom(), resultIqEntity.getSeconds()))

            def onError(errorIqEntity, originalIqEntity):
                logger.error("Error getting lastseen information for %s" %
                             originalIqEntity.getTo())

            entity = LastseenIqProtocolEntity(self.aliasToJid(jid))
            self._sendIq(entity, onSuccess, onError)

    @clicmd("Set profile picture")
    def profile_setPicture(self, path):
        if self.assertConnected():
            with PILOptionalModule(
                    failMessage="No PIL library installed, try install pillow") as imp:
                Image = imp("Image")

                def onSuccess(resultIqEntity, originalIqEntity):
                    self.tryPrint("Profile picture updated successfully")

                def onError(errorIqEntity, originalIqEntity):
                    logger.error("Error updating profile picture")

                src = Image.open(path)
                pictureData = src.resize((640, 640)).tobytes("jpeg", "RGB")
                picturePreview = src.resize((96, 96)).tobytes("jpeg", "RGB")
                iq = SetPictureIqProtocolEntity(self.getOwnJid(),
                                                picturePreview, pictureData)
                self._sendIq(iq, onSuccess, onError)

    @clicmd("Get profile privacy")
    def profile_getPrivacy(self):
        if self.assertConnected():

            def onSuccess(resultIqEntity, originalIqEntity):
                self.tryPrint("Profile privacy is: %s" % (resultIqEntity))

            def onError(errorIqEntity, originalIqEntity):
                logger.error("Error getting profile privacy")

            iq = GetPrivacyIqProtocolEntity()
            self._sendIq(iq, onSuccess, onError)

    @clicmd(
        "Profile privacy. value=all|contacts|none names=profile|status|last. Names are comma separated, defaults to all."
    )
    def profile_setPrivacy(self, value="all", names=None):
        if self.assertConnected():

            def onSuccess(resultIqEntity, originalIqEntity):
                self.tryPrint("Profile privacy set to: %s" % (resultIqEntity))

            def onError(errorIqEntity, originalIqEntity):
                logger.error("Error setting profile privacy")

            try:
                names = [name for name in names.split(',')] if names else None
                iq = SetPrivacyIqProtocolEntity(value, names)
                self._sendIq(iq, onSuccess, onError)
            except Exception as inst:
                self.tryPrint(inst.message)
                return self.print_usage()

################################################################################

#################################### groups ####################################

    @clicmd("List all groups you belong to", 5)
    def groups_list(self):
        if self.assertConnected():
            entity = ListGroupsIqProtocolEntity()
            self.toLower(entity)

    @clicmd("Leave a group you belong to", 4)
    def group_leave(self, group_jid):
        if self.assertConnected():
            entity = LeaveGroupsIqProtocolEntity([self.aliasToJid(group_jid)])
            self.toLower(entity)

    @clicmd(
        "Create a new group with the specified subject and participants. Jids are a comma separated list but optional.",
        3)
    def groups_create(self, subject, jids=None):
        if self.assertConnected():
            jids = [self.aliasToJid(jid)
                    for jid in jids.split(',')] if jids else []
            entity = CreateGroupsIqProtocolEntity(subject, participants=jids)
            self.toLower(entity)

    @clicmd("Invite to group. Jids are a comma separated list")
    def group_invite(self, group_jid, jids):
        if self.assertConnected():
            jids = [self.aliasToJid(jid) for jid in jids.split(',')]
            entity = AddParticipantsIqProtocolEntity(
                self.aliasToJid(group_jid), jids)
            self.toLower(entity)

    @clicmd("Promote admin of a group. Jids are a comma separated list")
    def group_promote(self, group_jid, jids):
        if self.assertConnected():
            jids = [self.aliasToJid(jid) for jid in jids.split(',')]
            entity = PromoteParticipantsIqProtocolEntity(
                self.aliasToJid(group_jid), jids)
            self.toLower(entity)

    @clicmd("Remove admin of a group. Jids are a comma separated list")
    def group_demote(self, group_jid, jids):
        if self.assertConnected():
            jids = [self.aliasToJid(jid) for jid in jids.split(',')]
            entity = DemoteParticipantsIqProtocolEntity(
                self.aliasToJid(group_jid), jids)
            self.toLower(entity)

    @clicmd("Kick from group. Jids are a comma separated list")
    def group_kick(self, group_jid, jids):
        if self.assertConnected():
            jids = [self.aliasToJid(jid) for jid in jids.split(',')]
            entity = RemoveParticipantsIqProtocolEntity(
                self.aliasToJid(group_jid), jids)
            self.toLower(entity)

    @clicmd("Change group subject")
    def group_setSubject(self, group_jid, subject):
        if self.assertConnected():
            entity = SubjectGroupsIqProtocolEntity(
                self.aliasToJid(group_jid), subject)
            self.toLower(entity)

    @clicmd("Set group picture")
    def group_picture(self, group_jid, path):
        if self.assertConnected():
            with PILOptionalModule(
                    failMessage=self.__class__.FAIL_OPT_PILLOW) as imp:
                Image = imp("Image")

                def onSuccess(resultIqEntity, originalIqEntity):
                    self.tryPrint("Group picture updated successfully")

                def onError(errorIqEntity, originalIqEntity):
                    logger.error("Error updating Group picture")

                src = Image.open(path)
                pictureData = src.resize((640, 640)).tobytes("jpeg", "RGB")
                picturePreview = src.resize((96, 96)).tobytes("jpeg", "RGB")
                iq = SetPictureIqProtocolEntity(
                    self.aliasToJid(group_jid), picturePreview, pictureData)
                self._sendIq(iq, onSuccess, onError)

    @clicmd("Get group info")
    def group_info(self, group_jid):
        if self.assertConnected():
            entity = InfoGroupsIqProtocolEntity(self.aliasToJid(group_jid))
            self.toLower(entity)

    @clicmd("Get shared keys")
    def keys_get(self, jids):
        with AxolotlOptionalModule(
                failMessage=self.__class__.FAIL_OPT_AXOLOTL) as importFn:
            importFn()
            from yowsup.layers.axolotl.protocolentities.iq_key_get import GetKeysIqProtocolEntity
            if self.assertConnected():
                jids = [self.aliasToJid(jid) for jid in jids.split(',')]
                entity = GetKeysIqProtocolEntity(jids)
                self.toLower(entity)

    @clicmd("Send init seq")
    def seq(self):
        priv = PrivacyListIqProtocolEntity()
        self.toLower(priv)
        push = PushIqProtocolEntity()
        self.toLower(push)
        props = PropsIqProtocolEntity()
        self.toLower(props)
        crypto = CryptoIqProtocolEntity()
        self.toLower(crypto)

    @clicmd("Delete your account")
    def account_delete(self):
        if self.assertConnected():
            if self.accountDelWarnings < self.__class__.ACCOUNT_DEL_WARNINGS:
                self.accountDelWarnings += 1
                remaining = self.__class__.ACCOUNT_DEL_WARNINGS - self.accountDelWarnings
                self.tryPrint(
                    "Repeat delete command another %s times to send the delete request"
                    % remaining)
            else:
                entity = UnregisterIqProtocolEntity()
                self.toLower(entity)

    @clicmd("Send message to a friend")
    def message_send(self, number, content):
        if self.assertConnected():
            outgoingMessage = TextMessageProtocolEntity(
                content.encode("utf-8")
                if sys.version_info >= (3, 0) else content,
                to=self.aliasToJid(number))
            self.toLower(outgoingMessage)

    @clicmd("Broadcast message. numbers should comma separated phone numbers")
    def message_broadcast(self, numbers, content):
        if self.assertConnected():
            jids = [self.aliasToJid(number) for number in numbers.split(',')]
            outgoingMessage = BroadcastTextMessage(jids, content)
            self.toLower(outgoingMessage)

    def message_read(self, message_id):
        pass

    def message_delivered(self, message_id):
        pass

    @clicmd("Send a video with optional caption")
    def video_send(self, number, path, caption=None):
        self.media_send(number, path,
                        RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO,
                        caption)

    @clicmd("Send an image with optional caption")
    def image_send(self, number, path, caption=None):
        self.media_send(number, path,
                        RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE,
                        caption)

    @clicmd("Send audio file")
    def audio_send(self, number, path):
        self.media_send(number, path,
                        RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO)

    def media_send(self, number, path, mediaType, caption=None):
        if self.assertConnected():
            jid = self.aliasToJid(number)
            entity = RequestUploadIqProtocolEntity(mediaType, filePath=path)
            successFn = lambda successEntity, originalEntity: self.onRequestUploadResult(jid, mediaType, path, successEntity, originalEntity, caption)
            errorFn = lambda errorEntity, originalEntity: self.onRequestUploadError(jid, path, errorEntity, originalEntity)
            self._sendIq(entity, successFn, errorFn)

            self._sendIq(entity, successFn, errorFn)

    @clicmd("Send typing state")
    def state_typing(self, jid):
        if self.assertConnected():
            entity = OutgoingChatstateProtocolEntity(
                ChatstateProtocolEntity.STATE_TYPING, self.aliasToJid(jid))
            self.toLower(entity)

    @clicmd("Request contacts statuses")
    def statuses_get(self, contacts):
        if self.assertConnected():
            entity = GetStatusesIqProtocolEntity(
                [self.aliasToJid(c) for c in contacts.split(',')])
            self.toLower(entity)

    @clicmd("Send paused state")
    def state_paused(self, jid):
        if self.assertConnected():
            entity = OutgoingChatstateProtocolEntity(
                ChatstateProtocolEntity.STATE_PAUSED, self.aliasToJid(jid))
            self.toLower(entity)

    @clicmd(
        "Sync contacts, contacts should be comma separated phone numbers, with no spaces"
    )
    def contacts_sync(self, contacts):
        if self.assertConnected():
            entity = GetSyncIqProtocolEntity(contacts.split(','))
            self.toLower(entity)

    @clicmd("Disconnect")
    def disconnect(self):
        if self.assertConnected():
            self.broadcastEvent(
                YowLayerEvent(YowNetworkLayer.EVENT_STATE_DISCONNECT))

    @clicmd("Quick login")
    def L(self):
        if self.connected:
            return self.tryPrint("Already connected, disconnect first")
        self.getLayerInterface(YowNetworkLayer).connect()
        return True

    @clicmd("Login to WhatsApp", 0)
    def login(self, username, b64password):
        self.setCredentials(username, b64password)
        return self.L()

################################################################################

################################### receive ####################################

    @ProtocolEntityCallback("chatstate")
    def onChatstate(self, entity):
        self.tryPrint(entity)

    @ProtocolEntityCallback("iq")
    def onIq(self, entity):
        self.tryPrint(entity)

    @ProtocolEntityCallback("receipt")
    def onReceipt(self, entity):
        self.toLower(entity.ack())

    @ProtocolEntityCallback("ack")
    def onAck(self, entity):
        if entity.getId() in self.ackQueue:
            self.ackQueue.pop(self.ackQueue.index(entity.getId()))

        if entity.getClass() == "message":
            self.tryPrint(entity.getId())

        if not len(self.ackQueue) and not self.workingOff:
            self.disconnect()

    @ProtocolEntityCallback("success")
    def onSuccess(self, entity):
        self.connected = True
        self.tryPrint("Logged in!")
        self.toLower(PresenceProtocolEntity(name=self.username))
        self.sendNews()

    @ProtocolEntityCallback("failure")
    def onFailure(self, entity):
        self.connected = False
        self.tryPrint("Login Failed, reason: %s" % entity.getReason())

    @ProtocolEntityCallback("notification")
    def onNotification(self, notification):
        notificationData = notification.__str__()
        if notificationData:
            self.tryPrint(notificationData)
        else:
            self.tryPrint("From :%s, Type: %s" %
                          (self.jidToAlias(notification.getFrom()),
                           notification.getType()))
        if self.sendReceipts:
            self.toLower(notification.ack())

    @ProtocolEntityCallback("message")
    def onMessage(self, message):
        messageOut = ""

        if not self.workingOff:
            if self.messageTimer:
                self.messageTimer.cancel()

            self.messageTimer = Timer(5.0, self.workOffMessageQueue, [])
            self.messageTimer.start()

        if message.getType() == "text":
            self.messageQueue.append(message)

            self.tryPrint("Message received! Send receipt.")
            self.toLower(message.ack())

            messageOut = self.getTextMessageBody(message)
        elif message.getType() == "media":
            messageOut = self.getMediaMessageBody(message)
        else:
            messageOut = "Unknown message type %s " % message.getType()
            self.tryPrint(messageOut.toProtocolTreeNode())

        formattedDate = datetime.datetime.fromtimestamp(message.getTimestamp(
        )).strftime('%d-%m-%Y %H:%M')
        sender = message.getFrom() if not message.isGroupMessage(
        ) else "%s/%s" % (message.getParticipant(False), message.getFrom())
        output = self.__class__.MESSAGE_FORMAT.format(
            FROM=sender,
            TIME=formattedDate,
            MESSAGE=messageOut.encode('latin-1').decode()
            if sys.version_info >= (3, 0) else messageOut.encode('utf-8'),
            MESSAGE_ID=message.getId())

        self.tryPrint(output)
        if message.getType() != "text" and self.sendReceipts:
            self.toLower(message.ack(self.sendRead))
            self.tryPrint("Sent delivered receipt" + " and Read"
                          if self.sendRead else "")

    def workOffMessageQueue(self):
        self.tryPrint("Working off messages ...")
        time.sleep(0.5)
        self.tryPrint("Be available.")
        self.toLower(AvailablePresenceProtocolEntity())
        time.sleep(1)

        contactMessageDict = defaultdict(list)

        for message in self.messageQueue:
            contactMessageDict[message.getFrom()].append(message)

        for msgFrom, messageList in contactMessageDict.items():
            for message in messageList:
                self.toLower(message.ack(True))
                del self.messageQueue[self.messageQueue.index(message)]

            if not message.isGroupMessage():
                time.sleep(randint(2, 3))
                self.tryPrint("Typing ...")
                typing = OutgoingChatstateProtocolEntity(
                    ChatstateProtocolEntity.STATE_TYPING, message.getFrom())
                self.toLower(typing)
                time.sleep(randint(2, 3))
                self.tryPrint("Pausing ...")
                paused = OutgoingChatstateProtocolEntity(
                    ChatstateProtocolEntity.STATE_PAUSED, message.getFrom())
                self.toLower(paused)
                time.sleep(randint(0, 1))
                self.tryPrint("Answer message.")
                answer = TextMessageProtocolEntity(
                    message.getBody(), to=message.getFrom())
                self.toLower(answer)
                time.sleep(randint(1, 2))

        if self.messageQueue:
            self.workOffMessageQueue()
        else:
            self.workingOff = False
            self.tryPrint("Be unavailable.")
            self.toLower(UnavailablePresenceProtocolEntity())

            if not self.sendingMedia:
                self.disconnect()

    def getTextMessageBody(self, message):
        return message.getBody()

    def getMediaMessageBody(self, message):
        if message.getMediaType() in ("image", "audio", "video"):
            return self.getDownloadableMediaMessageBody(message)
        else:
            return "[Media Type: %s]" % message.getMediaType()

    def getDownloadableMediaMessageBody(self, message):
        return "[Media Type:{media_type}, Size:{media_size}, URL:{media_url}]".format(
            media_type=message.getMediaType(),
            media_size=message.getMediaSize(),
            media_url=message.getMediaUrl())

    def doSendMedia(self, mediaType, filePath, url, to, ip=None, caption=None):
        if mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_IMAGE:
            entity = ImageDownloadableMediaMessageProtocolEntity.fromFilePath(
                filePath, url, ip, to, caption=caption)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_AUDIO:
            entity = AudioDownloadableMediaMessageProtocolEntity.fromFilePath(
                filePath, url, ip, to)
        elif mediaType == RequestUploadIqProtocolEntity.MEDIA_TYPE_VIDEO:
            entity = VideoDownloadableMediaMessageProtocolEntity.fromFilePath(
                filePath, url, ip, to, caption=caption)

        self.ackQueue.append(entity.getId())
        self.toLower(entity)
        self.sendingMedia = False

    def __str__(self):
        return "Newsbot Interface Layer"

################################################################################

################################## callbacks ###################################

    def onRequestUploadResult(self,
                              jid,
                              mediaType,
                              filePath,
                              resultRequestUploadIqProtocolEntity,
                              requestUploadIqProtocolEntity,
                              caption=None):
        if resultRequestUploadIqProtocolEntity.isDuplicate():
            self.doSendMedia(mediaType, filePath,
                             resultRequestUploadIqProtocolEntity.getUrl(), jid,
                             resultRequestUploadIqProtocolEntity.getIp(),
                             caption)
        else:
            successFn = lambda filePath, jid, url: self.doSendMedia(mediaType, filePath, url, jid, resultRequestUploadIqProtocolEntity.getIp(), caption)
            mediaUploader = MediaUploader(
                jid,
                self.getOwnJid(),
                filePath,
                resultRequestUploadIqProtocolEntity.getUrl(),
                resultRequestUploadIqProtocolEntity.getResumeOffset(),
                successFn,
                self.onUploadError,
                self.onUploadProgress)
            mediaUploader.start()

    def onRequestUploadError(self, jid, path,
                             errorRequestUploadIqProtocolEntity,
                             requestUploadIqProtocolEntity):
        logger.error("Request upload for file %s for %s failed" % (path, jid))
        self.sendingMedia = False

        if not self.workingOff:
            self.disconnect()

    def onUploadError(self, filePath, jid, url):
        logger.error("Upload file %s to %s for %s failed!" %
                     (filePath, url, jid))
        self.sendingMedia = False

        if not self.workingOff:
            self.disconnect()

    def onUploadProgress(self, filePath, jid, url, progress):
        self.tryPrint("%s => %s, %d%% \r" %
                      (os.path.basename(filePath), jid, progress))

    def onGetContactPictureResult(self, resultGetPictureIqProtocolEntiy,
                                  getPictureIqProtocolEntity):
        pass

    def __str__(self):
        return "Newsbot Interface Layer"

    @clicmd("Print this message")
    def help(self):
        self.print_usage()

    def tryPrint(self, string):
        if not self.verbose:
            print(string)
