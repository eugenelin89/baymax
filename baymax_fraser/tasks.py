import celery, os, requests, json

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
    elif action == 'q10' and parameters['ans']:
        print 'question 10'
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

def package_score(action, parameters):
    point = score_map[parameters['ans']]
    score = {'point':point, 'shade':0}
    if action in ['q1','q2','q3','q4','q5','q6','q7','q8']:
        if point >= 2:
            score['shade'] = 1
    elif point >= 1: #q9, shaded
        score['shade'] = 1
    return score


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



