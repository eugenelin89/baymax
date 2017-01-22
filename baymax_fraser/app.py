from __future__ import print_function
from flask import Flask, request, make_response, abort, logging
import urllib, json, os, sys, requests, tasks
# _access_token and _post_msg_url will eventually be moved to another module/process for sending messages.

#########
# Setup #
#########
app = Flask(__name__)

#########
# Flask #
#########

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def catch_all(path):
    abort(401)

@app.route("/test", methods=['GET'])
def test():
    tasks.add.delay(1,2)
    return "Good Test!"


##########
# API.AI #
##########

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)

    print("Request:")
    print(json.dumps(req, indent=4))

    res = processRequest(req)

    res = json.dumps(res, indent=4)
    # print(res)
    r = make_response(res)
    r.headers['Content-Type'] = 'application/json'
    return r


def processRequest(req):
    # Get incoming message
    sender_id = req.get("originalRequest").get("data").get("sender").get("id")
    sender_msg = req.get("originalRequest").get("data").get("message").get("text")
    response_msg = req.get("result").get("fulfillment").get("speech")
    timestamp = req.get("timestamp")
    action = req.get("result").get("action")
    parameters = req.get("result").get("parameters")
    tasks.store_dialog.delay(timestamp, sender_id, sender_msg, response_msg)
    tasks.process_user_response.delay(timestamp, sender_id, action, parameters)
    if "smalltalk" in req.get("result").get("action"):
        speech = req.get("result").get("fulfillment").get("speech")
        return {"speech": speech, "displayText":speech }
    return {}

#########################
# Old FB Messenger Code #
#########################

#  @app.route("/fb_webhook/<bot_id>", methods=['GET'])
#  def handshake(bot_id):
#      debug('Hello FooBar!')
#      debug(request.data)
#      token = request.args.get('hub.verify_token')
#      challenge = request.args.get('hub.challenge')
#      if token == os.environ['VERIFY_TOKEN'] and challenge != None: # need fix
#          return challenge
#      else:
#          abort(401)

#_post_msg_url = 'https://graph.facebook.com/v2.6/me/messages?access_token='+os.environ['FBOT_ACCESS_TOKEN']
test = 0
def testfunc(data):
    global test
    test = test + 1
    sender_id = data['entry'][0]['messaging'][0]['sender']['id']
    resp_data = {
        "recipient" : {"id":sender_id},
        "message" : {"text":"TEST -> "+str(test)}        
    }
    post_result = requests.post(_post_msg_url, json=resp_data)
    return post_result

@app.route("/fb_webhook/<bot_id>", methods=['POST'])
def process_message(bot_id):
    # received message from user
    debug('Process message...\n'+request.data)
    data = request.json # type dict, whereas request.data is type str
    tasks.process.delay(data)
    return "ok"


###########
# Helpers #
###########


def debug(message):
    print(message, file=sys.stderr)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
