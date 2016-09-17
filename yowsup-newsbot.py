#!/usr/bin/env python
__version__ = "2.0.15"
__author__ = "Tarek Galal"

import argparse
import logging
import sys
import yowsup
from yowsup.env import YowsupEnv

HELP_CONFIG = """
############# Yowsup Configuration Sample ###########
#
# ====================
# The file contains info about your WhatsApp account. This is used during registration and login.
# You can define or override all fields in the command line args as well.
#
# Country code. See http://www.ipipi.com/help/telephone-country-codes.htm. This is now required.
cc=49
#
# Your full phone number including the country code you defined in 'cc', without preceding '+' or '00'
phone=491234567890
#
# You obtain this password when you register using Yowsup.
password=NDkxNTIyNTI1NjAyMkBzLndoYXRzYXBwLm5ldA==
#######################################################
"""

CR_TEXT = """yowsup-newsbot  v{newsbotVersion}
yowsup      v{yowsupVersion}

Copyright (c) 2012-2016 Tarek Galal
http://www.openwhatsapp.org

This software is provided free of charge. Copying and redistribution is
encouraged.

If you appreciate this software and you would like to support future
development please consider donating:
http://openwhatsapp.org/yowsup/donate

"""

logger = logging.getLogger("yowsup-newsbot")

# logging.basicConfig(level=logging.DEBUG)
# logger = logging.getLogger(__name__)


class YowArgParser(argparse.ArgumentParser):
    def __init__(self, *args, **kwargs):
        super(YowArgParser, self).__init__(*args, **kwargs)

        self.add_argument(
            "-v",
            "--version",
            action="store_true",
            help="Print version info and exit")

        self.add_argument(
            "--help-config",
            action="store_true",
            help="Prints a config file sample", )

        self.add_argument(
            "-d", "--debug", action="store_true", help="Show debug messages")

        self.add_argument(
            "--verbose", action="store_true", help="Mute text output")

        self.args = {}
        self.verbose = False

    def getArgs(self):
        return self.parse_args()

    def getConfig(self, config):
        try:
            f = open(config)
            out = {}
            for l in f:
                line = l.strip()
                if len(line) and line[0] not in ('#', ';'):
                    prep = line.split('#', 1)[0].split(';', 1)[0].split('=', 1)
                    varname = prep[0].strip()
                    val = prep[1].strip()
                    out[varname.replace('-', '_')] = val
            return out
        except IOError:
            self.tryPrint("Invalid config path: %s" % config)
            sys.exit(1)

    def process(self):
        self.args = vars(self.parse_args())

        if self.args["version"]:
            self.tryPrint("yowsup-newsbot v%s\nUsing yowsup v%s" %
                          (__version__, yowsup.__version__))
            sys.exit(0)

        if self.args["help_config"]:
            self.tryPrint(HELP_CONFIG)
            sys.exit(0)

        if self.args["debug"]:
            logging.basicConfig(level=logging.DEBUG)
        else:
            logging.basicConfig(level=logging.INFO)

        if self.args["verbose"]:
            self.verbose = True

    def printInfoText(self):
        self.tryPrint(
            CR_TEXT.format(
                newsbotVersion=__version__, yowsupVersion=yowsup.__version__))

    def tryPrint(self, string):
        if not self.verbose:
            print(string)


class RegistrationArgParser(YowArgParser):
    def __init__(self, *args, **kwargs):
        super(RegistrationArgParser, self).__init__(*args, **kwargs)

        self.description = "WhatsApp registration options"

        configGroup = self.add_argument_group(
            "Configuration options",
            description="Config file is optional. Other configuration arguments have higher priority if given, and will override those specified in the config file")

        configGroup.add_argument(
            "-c",
            '--config',
            action="store",
            help='Path to config file. If this is not set then you must set at least --phone and --cc arguments')

        configGroup.add_argument(
            '-E',
            '--env',
            action="store",
            help="Set the environment yowsup simulates",
            choices=YowsupEnv.getRegisteredEnvs())

        configGroup.add_argument(
            "-m",
            '--mcc',
            action="store",
            help="Mobile Country Code. Check your mcc here: https://en.wikipedia.org/wiki/Mobile_country_code")

        configGroup.add_argument(
            "-n",
            '--mnc',
            action="store",
            help="Mobile Network Code. Check your mnc from https://en.wikipedia.org/wiki/Mobile_country_code")

        configGroup.add_argument(
            "-p",
            '--phone',
            action="store",
            help=" Your full phone number including the country code you defined in 'cc', without preceeding '+' or '00'")

        configGroup.add_argument(
            "-C",
            '--cc',
            action="store",
            help="Country code. See http://www.ipipi.com/networkList.do. This is now required")

        regSteps = self.add_argument_group("Modes")
        regSteps = regSteps.add_mutually_exclusive_group()

        regSteps.add_argument(
            "-r",
            '--requestcode',
            help='Request the digit registration code from Whatsapp.',
            action="store",
            required=False,
            metavar="(sms|voice)")

        regSteps.add_argument(
            "-R",
            '--register',
            help='Register account on Whatsapp using the code you previously received',
            action="store",
            required=False,
            metavar="code")

    def process(self):
        super(RegistrationArgParser, self).process()

        config = self.getConfig(self.args["config"]) if self.args[
            "config"] else {}

        if self.args["env"]:
            YowsupEnv.setEnv(self.args["env"])

        if self.args["mcc"]:
            config["mcc"] = self.args["mcc"]

        if self.args["mnc"]:
            config["mnc"] = self.args["mnc"]

        if self.args["phone"]:
            config["phone"] = self.args["phone"]

        if self.args["cc"]:
            config["cc"] = self.args["cc"]

        if not "mcc" in config:
            config["mcc"] = "000"

        if not "mnc" in config:
            config["mnc"] = "000"

        if not "sim_mcc" in config:
            config["sim_mcc"] = "000"

        if not "sim_mnc" in config:
            config["sim_mnc"] = "000"

        try:
            assert self.args["requestcode"] or self.args[
                "register"], "Must specify one of the modes -r/-R"
            assert "cc" in config, "Must specify cc (country code)"
            assert "phone" in config, "Must specify phone number"
        except AssertionError as e:
            self.tryPrint(e)
            self.tryPrint("\n")
            return False

        if not config["phone"].startswith(config["cc"]):
            self.tryPrint(
                "Error, phone number does not start with the specified country code\n")
            return False

        config["phone"] = config["phone"][len(config["cc"]):]

        if self.args["requestcode"]:
            self.handleRequestCode(self.args["requestcode"], config)
        elif self.args["register"]:
            self.handleRegister(self.args["register"], config)
        else:
            return False

        return True

    def handleRequestCode(self, method, config):
        from yowsup.registration import WACodeRequest
        self.printInfoText()
        codeReq = WACodeRequest(config["cc"], config["phone"], config["mcc"],
                                config["mnc"], config["mcc"], config["mnc"],
                                method)
        result = codeReq.send()
        self.tryPrint(self.resultToString(result))

    def handleRegister(self, code, config):
        from yowsup.registration import WARegRequest
        self.printInfoText()
        code = code.replace('-', '')
        req = WARegRequest(config["cc"], config["phone"], code)
        result = req.send()
        self.tryPrint(self.resultToString(result))

    def resultToString(self, result):
        unistr = str if sys.version_info >= (3, 0) else unicode
        out = []
        for k, v in result.items():
            if v is None:
                continue
            out.append("%s: %s" % (k, v.encode("utf-8")
                                   if type(v) is unistr else v))

        return "\n".join(out)


class DemosArgParser(YowArgParser):
    def __init__(self, *args, **kwargs):
        super(DemosArgParser, self).__init__(*args, **kwargs)

        self.description = "Run a yowsup demo"

        configGroup = self.add_argument_group(
            "Configuration options for demos")
        credentialsOpts = configGroup.add_mutually_exclusive_group()

        credentialsOpts.add_argument(
            "-l",
            "--login",
            action="store",
            metavar="phone:b64password",
            help="WhatsApp login credentials, in the format phonenumber:password, where password is base64 encoded.")

        credentialsOpts.add_argument(
            "-c",
            "--config",
            action="store",
            help="Path to config file containing authentication info. For more info about config format use --help-config")

        configGroup.add_argument(
            '-E',
            '--env',
            action="store",
            help="Set the environment yowsup simulates",
            choices=YowsupEnv.getRegisteredEnvs())

        configGroup.add_argument(
            "-M",
            "--unmoxie",
            action="store_true",
            help="Disable E2E Encryption")

        cmdopts = self.add_argument_group("Command line interface demo")

        cmdopts.add_argument(
            '-n',
            '--news',
            action="store",
            metavar="date",
            help="Start the news bot")

    def process(self):
        super(DemosArgParser, self).process()

        if self.args["env"]:
            YowsupEnv.setEnv(self.args["env"])

        if self.args["news"]:
            self.startNews()
        else:
            return False
        return True

    def _getCredentials(self):
        if self.args["login"]:
            return tuple(self.args["login"].split(":"))
        elif self.args["config"]:
            config = self.getConfig(self.args["config"])
            assert "password" in config and "phone" in config, "Must specify at least phone number and password in config file"
            return config["phone"], config["password"]
        else:
            return None

    def startNews(self):
        import newsbot

        credentials = self._getCredentials()

        if not credentials:
            self.tryPrint("Error: You must specify a configuration method")
            sys.exit(1)

        self.printInfoText()
        stack = newsbot.YowsupNewsbotStack(credentials, self.args["news"],
                                           not self.args["unmoxie"],
                                           self.verbose)
        stack.start()


if __name__ == "__main__":
    args = sys.argv
    if (len(args) > 1):
        del args[0]

    modeDict = {
        "demos": DemosArgParser,
        "registration": RegistrationArgParser,
        "version": None
    }

    if (len(args) == 0 or args[0] not in modeDict):
        self.tryPrint("Available commands:\n===================")
        self.tryPrint(", ".join(modeDict.keys()))

        sys.exit(1)

    mode = args[0]
    if mode == "version":
        self.tryPrint("yowsup-newsbot v%s\nUsing yowsup v%s" %
                      (__version__, yowsup.__version__))
        sys.exit(0)
    else:
        parser = modeDict[mode]()
        if not parser.process():
            parser.print_help()
