import celery, os, requests, json, tasks

#_post_msg_url = 'https://graph.facebook.com/v2.6/me/messages?access_token='+os.environ['FBOT_ACCESS_TOKEN']


app = celery.Celery('demo')
app.conf.update(BROKER_URL=os.environ['CLOUDAMQP_URL'],BROKER_POOL_LIMIT=20)


##########
# Celery #
##########

@app.task
def add(x,y):
    print 'testing add'
    return x+y


##########
# API.AI #
##########

@app.task
def store_dialog(timestamp, sender_id, sender_msg, response_msg):
    # 1. store message to db by POST to baymax_firebase
    post_url = os.environ['POST_MSG_URL']
    print 'POST to ' + post_url
    data = {'timestamp':timestamp,'sender_id':sender_id, 'sender_msg':sender_msg, 'response_message':response_msg}
    requests.post(post_url, json=data)
    return

@app.task
def process_user_response(timestamp, sender_id, action, parameters):
    # 1. Keep Score
    if action in ['q1','q2','q3','q4','q5','q6','q7','q8','q9'] and parameters['ans']:
        # need to calc score
        # points 0, 1, 2, 3
        # shade 0, 1
        post_url = os.environ['POST_SCORE_URL']
        score = package_score(action, parameters)
        score['question'] = action
        score['timestamp'] = timestamp
        score['sender_id'] = sender_id
        print action+' ans= '+parameters['ans']
        print 'score object: '+json.dumps(score)
        requests.post(post_url, json=score)
        if action == 'q9':
            print 'ABOUT TO PROCESS Q9'
            process_q9_q10(sender_id)
    elif action == 'q10' and parameters['difficulty']:
        print 'question 10'
        score = calc_total_score(sender_id)['score']
        complete_q(sender_id, score)
    elif action == 'start_collect':
        print 'starting to collect user info...'
        if parameters['yes_no'] == 'yes':
            print 'collect user info'
            collect_sender_info(sender_id)
        else:
            print 'flag use based on FB name'
            send_fb_message(sender_id, "OK... Please check back with me soon!")
    else:
        print 'not an answer'
    return


###########
# Helpers #
###########
score_map = {
    'never':0,
    'few days':1,
    'a week':2,
    'everyday':3    
}

def calc_total_score(sender_id):
    # Get the scores from datasource
    get_url = os.environ['GET_SCORE_URL']
    d = requests.get(get_url, params={'sender_id':sender_id}).json()
    print 'scores: '+json.dumps(d, indent=4)
    # Sum all questions answered.
    score = 0
    shade = 0
    for key in d:
        score += d[key]['score']
        shade += d[key]['shade']
    print 'TOTAL SCORE '+str(score)
    return {'score':score, 'shade':shade}

def package_score(action, parameters):
    point = score_map[parameters['ans']]
    score = {'score':point, 'shade':0}
    if action in ['q1','q2','q3','q4','q5','q6','q7','q8']:
        if point >= 2:
            score['shade'] = 1
    elif point >= 1: #q9, shaded
        score['shade'] = 1 
    return score

def complete_q(sender_id, score):
    print 'C O M P L E T E   Q U E S T I O N A I R E'
    # Based on the score, we have a 3 options
    # Option 1: Refer some resources
    # Option 2: Ask if they'd like to be contacted
    if score >= 5:
        print 'collect sender info'
        sender_info = start_collect_sender_info(sender_id)
    else:
        msg = 'You are good! But do let me know if you want to talk!'
        send_fb_message(sender_id, msg)
    # Option 3: Ask if they'd like to be contacted, and set alert
        
    return

def collect_sender_info(sender_id):
    print 'actually collect sender info'
    profile = get_fb_profile(sender_id)
    first_name = profile['first_name']
    last_name = profile['last_name']
    print 'sender name: '+first_name+' '+last_name
    msg = first_name+' , what is the best way to contact you? Please provide us your contact preference and information?'
    send_fb_message(sender_id, msg)
    
    return



def get_fb_profile(sender_id):
    # get facebok profile
    get_url = os.environ['GET_PROFILE_URL']
    j = requests.get(get_url, params={'sender_id':sender_id}).json()
    return j

def start_collect_sender_info(sender_id):
    msg = 'Based on your answers, I would really recommend talking to someone. Would you like someone to give you a call and talk it out?'
    quick_replies = [
        {
            "content_type":"text",
            "title":"yes please",
            "payload":"yes please"
        },
        {
            "content_type":"text",
            "title":"no, please leave me alone",
            "payload":"no, please leave me alone"
        }
    ]
    send_fb_message(sender_id, msg, quick_replies)
    return

def process_q9_q10(sender_id):
    print 'PROCESSING Q9'
    score = calc_total_score(sender_id)['score']
    # if sume > 1, invoke event for q10
    if score > 0:
        ask_q10(sender_id)
    else:
        complete_q(sender_id, score)
    return score

def send_fb_message(sender_id, message, quick_reply = None):
    post_msg_url = 'https://graph.facebook.com/v2.6/me/messages?access_token='+os.environ['FB_ACCESS_TOKEN']
    resp_data = {
        "recipient":{"id":sender_id},
        "message":{"text":message}
    }
    if quick_reply != None:
        resp_data["message"]["quick_replies"] = quick_reply
    res = requests.post(post_msg_url, json=resp_data)
    return res 

def ask_q10(sender_id):
    send_fb_message(sender_id, "OK... I need to ask you one more question...")
    quick_replies = [
            {
                "content_type":"text",
                "title":"not at all",
                "payload":"not at all"
            },
            {
                "content_type":"text",
                "title":"somewhat",
                "payload":"somewhat"
            },
            {
                "content_type":"text",
                "title":"very",
                "payload":"very"
            },
            {
                "content_type":"text",
                "title":"extremely",
                "payload":"extremely"
            }] 
    msg = "How difficult have the problems made it for you to do your work, take care of things at home, or get along with other people?"
    send_fb_message(sender_id, msg ,quick_replies)

    return

#########################
# Old FB Messenger Code #
#########################

# @app.task
# def process(data):
#     if 'message' in data['entry'][0]['messaging'][0]: # The 'messaging' array may contain multiple messages.  Need fix.
#         sender_id = data['entry'][0]['messaging'][0]['sender']['id']
#         message = data['entry'][0]['messaging'][0]['message']['text']
#         # sending messages will be moved out of this module.
#         resp_data = {
#             "recipient" : {"id":sender_id},
#             "message" : {"text":str(message)}        
#         }
#         print 'POST RESPONSE BACK TO: '+ _post_msg_url
#         post_result = requests.post(_post_msg_url, json=resp_data)
#         print post_result
#     return



