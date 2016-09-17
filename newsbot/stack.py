import logging
import sys
from yowsup.layers import YowLayerEvent
from yowsup.layers.auth import AuthError
from yowsup.layers.axolotl.props import PROP_IDENTITY_AUTOTRUST
from yowsup.stacks import YowStackBuilder

from .layer import YowsupNewsbotLayer


class YowsupNewsbotStack(object):
    def __init__(self,
                 credentials,
                 date,
                 encryptionEnabled=True,
                 verbose=False):
        stackBuilder = YowStackBuilder()

        self.stack = stackBuilder.pushDefaultLayers(encryptionEnabled).push(
            YowsupNewsbotLayer(date, verbose)).build()

        self.stack.setCredentials(credentials)
        self.stack.setProp(PROP_IDENTITY_AUTOTRUST, True)

    def start(self):
        self.stack.broadcastEvent(
            YowLayerEvent(YowsupNewsbotLayer.EVENT_START))

        try:
            self.stack.loop(timeout=0.5, discrete=0.5)
        except AuthError as e:
            print("Auth Error, reason %s" % e)
        except KeyboardInterrupt:
            print("\nYowsdown")
            sys.exit(0)
