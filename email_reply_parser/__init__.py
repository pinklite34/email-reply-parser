"""
    email_reply_parser is a python library port of GitHub's Email Reply Parser.

    For more information, visit https://github.com/zapier/email-reply-parser
"""

import re


class EmailReplyParser(object):
    """ Represents a email message that is parsed.
    """

    @staticmethod
    def read(text):
        """ Factory method that splits email into list of fragments

            text - A string email body

            Returns an EmailMessage instance
        """
        return EmailMessage(text).read()

    @staticmethod
    def parse_reply(text):
        """ Provides the reply portion of email.

            text - A string email body

            Returns reply body message
        """
        return EmailReplyParser.read(text).reply


class EmailMessage(object):
    """ An email message represents a parsed email body.
    """

    SIG_REGEX = re.compile(r'(--|__|-\w)|(^Sent from my (\w+\s*){1,3})')
    QUOTE_HDR_REGEX = re.compile('On.*wrote:$')
    QUOTED_REGEX = re.compile(r'(>+)')
    HEADER_REGEX = re.compile(r'^\*?(From|Sent|To|Subject):\*? .+')
    _MULTI_QUOTE_HDR_REGEX = r'(?!On.*On\s.+?wrote:)(On\s(.+?)wrote:)'
    MULTI_QUOTE_HDR_REGEX = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL | re.MULTILINE)
    MULTI_QUOTE_HDR_REGEX_MULTILINE = re.compile(_MULTI_QUOTE_HDR_REGEX, re.DOTALL)

    def __init__(self, text):
        self.fragments = []
        self.fragment = None
        self.text = text.replace('\r\n', '\n')
        self.found_visible = False

    def read(self):
        """ Creates new fragment for each line
            and labels as a signature, quote, or hidden.

            Returns EmailMessage instance
        """

        self.found_visible = False

        is_multi_quote_header = self.MULTI_QUOTE_HDR_REGEX_MULTILINE.search(self.text)
        if is_multi_quote_header:
            self.text = self.MULTI_QUOTE_HDR_REGEX.sub(is_multi_quote_header.groups()[0].replace('\n', ''), self.text)

        # Fix any outlook style replies, with the reply immediately above the signature boundary line
        #   See email_2_2.txt for an example
        self.text = re.sub('([^\n])(?=\n ?[_-]{7,})', '\\1\n', self.text, re.MULTILINE)

        self.lines = self.text.split('\n')
        self.lines.reverse()

        for line in self.lines:
            self._scan_line(line)

        self._finish_fragment()

        self.fragments.reverse()

        return self

    @property
    def reply(self):
        """ Captures reply message within email
        """
        reply = []
        for f in self.fragments:
            if not (f.hidden or f.quoted):
                reply.append(f.content)
        return '\n'.join(reply)

    def _scan_line(self, line):
        """ Reviews each line in email message and determines fragment type

            line - a row of text from an email message
        """
        is_quote_header = self.QUOTE_HDR_REGEX.match(line) is not None
        is_quoted = self.QUOTED_REGEX.match(line) is not None
        is_header = is_quote_header or self.HEADER_REGEX.match(line) is not None

        if self.fragment and len(line.strip()) == 0:
            if self.SIG_REGEX.match(self.fragment.lines[-1].strip()):
                self.fragment.signature = True
                self._finish_fragment()

        if self.fragment \
                and ((self.fragment.headers == is_header and self.fragment.quoted == is_quoted) or
                         (self.fragment.quoted and (is_quote_header or len(line.strip()) == 0))):

            self.fragment.lines.append(line)
        else:
            self._finish_fragment()
            self.fragment = Fragment(is_quoted, line, headers=is_header)

    def quote_header(self, line):
        """ Determines whether line is part of a quoted area

            line - a row of the email message

            Returns True or False
        """
        return self.QUOTE_HDR_REGEX.match(line[::-1]) is not None

    def _finish_fragment(self):
        """ Creates fragment
        """

        if self.fragment:
            self.fragment.finish()
            if self.fragment.headers:
                # Regardless of what's been seen to this point, if we encounter a headers fragment,
                # all the previous fragments should be marked hidden and found_visible set to False.
                self.found_visible = False
                for f in self.fragments:
                    f.hidden = True
            if not self.found_visible:
                if self.fragment.quoted \
                        or self.fragment.headers \
                        or self.fragment.signature \
                        or (len(self.fragment.content.strip()) == 0):

                    self.fragment.hidden = True
                else:
                    self.found_visible = True
            self.fragments.append(self.fragment)
        self.fragment = None


class Fragment(object):
    """ A Fragment is a part of
        an Email Message, labeling each part.
    """

    def __init__(self, quoted, first_line, headers=False):
        self.signature = False
        self.headers = headers
        self.hidden = False
        self.quoted = quoted
        self._content = None
        self.lines = [first_line]

    def finish(self):
        """ Creates block of content with lines
            belonging to fragment.
        """
        self.lines.reverse()
        self._content = '\n'.join(self.lines)
        self.lines = None

    @property
    def content(self):
        return self._content.strip()
# Colour constants
bold=`tput bold`
green=`tput setaf 2`
red=`tput setaf 1`
reset=`tput sgr0`

ALICE_PORT=10001
BOB_PORT=10002

ALICE_LOG=bin/testnet/test/alice.txt
BOB_LOG=bin/testnet/test/bob.txt

if test -d bin; then cd bin; fi

echo "${bold}Mounting a RAM disk for server output in test directory!${reset}"
if mountpoint -q -- "test"; then
    sudo umount test
fi

rm -r test | true # in case this is the first time being run
mkdir test && sudo mount -t tmpfs -o size=5000m tmpfs test

# Source Intel Libraries
source /opt/intel/sgxsdk/environment

pushd ../../ # go to source directory
echo "${bold}Starting two ghost teechain enclaves...${reset}"

echo "${bold}Spawning enclave ALICE listening on port $ALICE_PORT in $ALICE_LOG ${reset}"
./teechain ghost -d -p $ALICE_PORT > $ALICE_LOG 2>&1 &
sleep 1

echo "${bold}Spawning enclave BOB listening on port $BOB_PORT in $BOB_LOG ${reset}"
./teechain ghost -d -p $BOB_PORT > $BOB_LOG 2>&1 &
sleep 1

echo -n "${red}Waiting until enclaves are initialized ...!${reset}"
for u in alice bob; do  #TODO: generalize to multiple parties (not just 4)
    while [ "$(grep -a 'Enclave created' bin/testnet/test/${u}.txt | wc -l)" -eq 0 ]; do
        sleep 0.1
        echo -n "."
    done
done

# Create primaries
./teechain primary -p $ALICE_PORT
./teechain primary -p $BOB_PORT

# Setup up primaries with number of deposits
./teechain setup_deposits 5 -p $ALICE_PORT
./teechain setup_deposits 3 -p $BOB_PORT

# Deposits made
./teechain deposits_made mmY6ijr6uLP3DdRFC4nwL23HSKsH2xgy74 1 5 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feA 0 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feA 1 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feA 2 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feA 3 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feA 4 1 -p $ALICE_PORT
./teechain deposits_made my6NJU1T6gL5f3TfmSPN4idUytdCQHTmsU 1 3 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feB 0 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feB 1 1 edec34c9bb3a4395cd8d1e9300725f537235d8a058fc6a7ae519003b64fd0feB 2 1  -p $BOB_PORT

# Create and establish a channel between Alice and Bob
./teechain create_channel -p $BOB_PORT &
sleep 1
./teechain create_channel -i -r 127.0.0.1:$BOB_PORT -p $ALICE_PORT # Initiator

sleep 2

# Extract the channel id for the channel created
CHANNEL_1=$(grep "Channel ID:" $ALICE_LOG | awk '{print $3}')

# Verified the setup transactions are in the blockchain
./teechain verify_deposits $CHANNEL_1 -p $BOB_PORT &
./teechain verify_deposits $CHANNEL_1 -p $ALICE_PORT

sleep 2

# Alice and Bob add deposits to their channels now
./teechain add_deposit $CHANNEL_1 0 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 0 -p $BOB_PORT

# Alice check balance matches expected
./teechain balance $CHANNEL_1 -p $ALICE_PORT
if ! tail -n 2 $ALICE_LOG | grep -q "My balance is: 1, remote balance is: 1"; then
    echo "Alice's balance check failed on channel setup!"; exit 1;
fi

# Send from Bob to Alice
./teechain send $CHANNEL_1 1 -p $BOB_PORT

# Alice check balance after
./teechain balance $CHANNEL_1 -p $ALICE_PORT
if ! tail -n 2 $ALICE_LOG | grep -q "My balance is: 2, remote balance is: 0"; then
    echo "Alice's balance check failed after send!"; exit 1;
fi

# Send from Bob to Alice should fail. Bob check balance, shouldn't have changed
./teechain send $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 2"; then
    echo "Bob's balance check failed!"; exit 1;
fi
# Add deposit from bob's side and check balance
./teechain add_deposit $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 1, remote balance is: 2"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob added another deposit to his channel!"
# Send from Bob to Alice and check balance is back to zero
./teechain send $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 3"; then
    echo "Bob's balance check failed!"; exit 1;
fi
# Send from Alice to Bob and check Bob's balance on Alice's side
./teechain send $CHANNEL_1 1 -p $ALICE_PORT
./teechain balance $CHANNEL_1 -p $ALICE_PORT
if ! tail -n 2 $ALICE_LOG | grep -q "My balance is: 2, remote balance is: 1"; then
    echo "Alice's balance check failed!"; exit 1;
fi
# Bob remove deposit and check balance
./teechain remove_deposit $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 2"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob removed the deposit from his channel!"
# Bob try to remove first deposit, should fail as insufficient funds
./teechain remove_deposit $CHANNEL_1 0 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 2"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob removed his last deposit from the channel!"
# Bob now send 1 to alice
./teechain send $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 1"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob sent 1 to Alice!"
# Alice removed last deposit from channel
./teechain remove_deposit $CHANNEL_1 0 -p $ALICE_PORT
./teechain balance $CHANNEL_1 -p $ALICE_PORT
if ! tail -n 2 $ALICE_LOG | grep -q "My balance is: 0, remote balance is: 0"; then
    echo "Alice's balance check failed!"; exit 1;
fi
echo "Alice removed her last deposit from the channel!"
# Bob now send 1 to alice
./teechain send $CHANNEL_1 1 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 0"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob tried to send 1 to alice, but it didnt work!"
# Add all the deposits to the channel (both sides)
./teechain add_deposit $CHANNEL_1 0 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 1 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 2 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 3 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 4 -p $ALICE_PORT
./teechain add_deposit $CHANNEL_1 0 -p $BOB_PORT
./teechain add_deposit $CHANNEL_1 1 -p $BOB_PORT
./teechain add_deposit $CHANNEL_1 2 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $ALICE_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $ALICE_LOG | grep -q "My balance is: 5, remote balance is: 3"; then
    echo "Alice's balance check failed!"; exit 1;
fi
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 3, remote balance is: 5"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "All deposits added to the channel!"
# Bob now send 3 to alice
./teechain send $CHANNEL_1 3 -p $BOB_PORT
./teechain balance $CHANNEL_1 -p $BOB_PORT
if ! tail -n 2 $BOB_LOG | grep -q "My balance is: 0, remote balance is: 8"; then
    echo "Bob's balance check failed!"; exit 1;
fi
echo "Bob sent all 3 to Alice!"
# Settle and shutdown
./teechain settle_channel $CHANNEL_1 -p $ALICE_PORT
# Alice decides to get her unused deposits out (there are no used deposits!)
./teechain shutdown -p $ALICE_PORT
popd # return to bin directory
../kill.sh
echo "${bold}Looks like the test passed!${reset}"
  -----BEGIN CERTIFICATE-----
MIIDhTCCAm2gAwIBAgIJALjCgEBIwDscMA0GCSqGSIb3DQEBBQUAMFkxCzAJBgNV
BAYTAkFVMRMwEQYDVQQIDApTb21lLVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBX
aWRnaXRzIFB0eSBMdGQxEjAQBgNVBAMMCWxvY2FsaG9zdDAeFw0xMzAzMDgxMzQw
MDJaFw0yMzAzMDYxMzQwMDJaMFkxCzAJBgNVBAYTAkFVMRMwEQYDVQQIDApTb21l
LVN0YXRlMSEwHwYDVQQKDBhJbnRlcm5ldCBXaWRnaXRzIFB0eSBMdGQxEjAQBgNV
BAMMCWxvY2FsaG9zdDCCASIwDQYJKoZIhvcNAQEBBQADggEPADCCAQoCggEBAOTL
p47Qy1hovBC6VWi33CCpq5r5+QHnt5PLsjhOoZ0VjHI0KYNMPkT9yfwJZO8vHEsW
dDoW+fRojp+VO6JOYcO1JAr0jBlnzfOlr+zBHKvaEWylku9DS5ZbxLnj4AQe5m5/
uqtlQt4ib4vXQr3yfW8B9Jy55OfWV8m9orfxubOzK1Ll0LeDwubKgUwuzB3auJKb
VNsIlZQzrKDzMoTExtKF/7cSUC+5+1UHFy9rUh9VOtU2RkFJQgOPOyw9lmg7pCfl
uurz4Q8wjSchhWvMnEc8YenqOaA+AcmlFiHwQq3z0aILCa5IEUOUzwER4bZM6eDe
8rZLG+uRAABhhfC/LfUCAwEAAaNQME4wHQYDVR0OBBYEFEhAKuSwT9BxLaHcxzmn
CDZ7bxycMB8GA1UdIwQYMBaAFEhAKuSwT9BxLaHcxzmnCDZ7bxycMAwGA1UdEwQF
MAMBAf8wDQYJKoZIhvcNAQEFBQADggEBAIK1pI70uzMET8QAJ6o0rBsuYnat9WeL
Y/27yKWg440BoWYxI6XJPP+nnncesGxcElnQCPkut8ODIGG037WKuQNRMr7dBQeU
MIaIxKGZETGIj5biao6tqYuWwIS54NxOTIUVx4QomXnyLNyE0Mj4ftD8bKEIuVfV
2bDC6UjN02lPh2IsV+th5oOr3BShwafu+7CAKLSaidraUW/hGKSWpMgBSBHnA2tD
W3mLidFxB2ufi6ufT87HliC6AJw6S9A5+iuAIEuRGV4zhc4BZpKTeeFRVWYPUBtp
/SoNIeLQ4ORhIFQjTY2nEq2lGnCJ0JcTTt1gVNbsEitRtw0eAUtMTXs=
-----END CERTIFICATE-----
-----BEGIN RSA PRIVATE KEY-----
MIIEpAIBAAKCAQEAuZ4RZVnjh8kS32TZn7pMWJevf473pLqecObWMLmeB6FIzpvf
kYi8RyLD9Q87QjmIhbrqFncyaBaw1iz5sx2sVM2+acwlocN4UHPBCxwvmtUeEn1t
WMp29D4NetJNssvq7PxzcXY7bv7FQ7q7kJ5KpoBc+OBu/4vdQhM0gkR5QEL52KNj
C8umfhc2aEeRn4et9lBqNlE4WjH3s5tOO3DqNt5kQ28hulcSaiPMaKPcjqmAYz8+
VLOY7fefGNBecr72MaA5St+oc0TDK6msHPoTtYe4b6r6AsyM9O+7f82idtWK9nu/
rjQZP2UeMQvqUtQj+Ar3WoM60SkEQ8Ckq6PQPwIDAQABAoIBAFUlZFd4r34HR8gA
LDAwNnthQZkjDQicrredvF1nmE1pt8tHB3xsG+oJ0Zgln4pWeADYaC9cCFxlJENr
KDP5Bad1JcbEZfLZhuRo5QHisRe2cXAL51AWuBB8MpTHyeqdzitd9tryYHsfFYBn
NUk2w4mzUnK8CU7iauG3i5vCK1jFV9OvedeQGjmKcJ39U4R8qOQesTP1x0tc7C8Y
SgSNaicZKXcHOlHntk6sGfpCekDX0bPKAOB2CMtbujeUNB/wgM/eEGLugdddXHfV
GErnqqnSCUog3bhZLaEOdl4XOJZtBmKIzQcUecNH3myADgpSm+AethCYErRqmvIj
FhXNfVkCgYEA7B2NjuOeaxoIgqPVN+DFVOVOv25AODLpgZDrfPZqr0E231LaexRn
xtsuJpxQ/lGPgY6dOrhX6d5HEQ2JrFDiKyv+uP7V/s9Wp562UhSMRLzuXWg7phto
yuia2bwj9k4Fwl9b3tQfJMxUulv2Bkq4+ZtuX0bFw8P4C3xwQMLQCgMCgYEAyT/S
UFIFp2u/7tXce5qrT3Z/SMe3qa+1DeosmhdCNQdJhV0p7rARX0bl+UN1oeDg65Sb
khzmTf+zpB0Nho63+W/CjlSdHBBFPTgSgjejkfiENfW63HBT18K0ya2LC4+fOuWg
e35VBJjKZT4nUTjZ/rscdeKNve4SvSWl3dFPqhUCgYEAgqIbJroydKkTmkvQdLjs
FHtF5U23RCCO5ntqflnLTqkzFb2+WShB/lhXoU8M1JgFYLWpsco6AY9UHFA0Il0h
tKcDqBB+Dxthox2BW8o4jPNGofFARzeU8+ZbfinEb8pdD1w49QDBNlfCbNTiOjrv
OlJPb3E1i4kJ3Dj91iayeUcCgYEAgS5qfgxofLN5nIHC6cS6umNCCSHKDy4udiQf
RTow0YE//E91HzX9sL792CcpVyPWvOHDiuLqIp9EXNAZYooyJfdLV7mQr/bxuv5H
Qzcb1BNGKqz1qZKg/xqImfzACEfE2jWT8jGBuVWqdZqT+lsX85+AAVvPyF8NwERu
WBiHnpECgYA28LMcfOVplez7z7wxzoVZyq7I7yV50RCxZiJ6GepZPzTnqR2LAmb6
2qMOJkShHk/pydtF+49j9/MjWJexGWaCbsFaei/bnsZfskEF+/2MFmBp6fAN1FRP
FLNEF+YTPz6yFCNWecZ2INEAokEi2D809XhDQwiJz0E2vEzhR93fDg==
-----END RSA PRIVATE KEY-----
  
