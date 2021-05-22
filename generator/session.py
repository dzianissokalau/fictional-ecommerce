from datetime import datetime, timedelta
import numpy as np

import sys
import os

sys.path.append(os.path.realpath('../'))
from generator import users, items


def session(user_id, timestamp, platform, country, events, satisfaction_impact):
    users[user_id].visit(timestamp=timestamp, platform=platform, country=country)
    
    # number of the event
    n = 0
    
    while users[user_id].active_session:
        last_event = users[user_id].last_event
        
        next_events = events[last_event]['next_events'].copy()
        probabilities = events[last_event]['probabilities'].copy()
                        
        
        # adjust registration probability
        if users[user_id].registered == False and 'create_account' not in next_events:
            # add registration as potential event
            next_events.append('create_account')
            probabilities = [prob * 0.8 for prob in probabilities]
            probabilities.append(0.2)

        
        # adjust open basket probability
        if users[user_id].n_items_in_basket > 0 \
                and users[user_id].last_event not in ['open_basket', 'remove_from_basket'] \
                and 'open_basket' not in next_events:
            next_events.append('open_basket')
            probabilities = [prob * 0.8 for prob in probabilities]
            probabilities.append(0.2)         
        
        
        # with every event probability of do nothing grows
        if 'do_nothing' in next_events:
            index = next_events.index('do_nothing')
            probabilities[index] = probabilities[index] * (1 + n/100)
            
        
        # check condition for every event
        for event in next_events.copy():
            if 'conditions' in events[event]:
                for condition in events[event]['conditions']:
                    if eval(f'users[user_id].{condition}') == False:
                        index = next_events.index(event)
                        next_events.remove(event)
                        probabilities.pop(index) 
                        break
                        
            
        # normalize probabilities
        total_p = sum(probabilities)
        probabilities = [p/total_p for p in probabilities]
        probabilities[0] = probabilities[0] + 1-sum(probabilities) 
        
        rand = np.random.default_rng(seed=timestamp.minute*60+timestamp.second+user_id)
        next_event = rand.choice(a=next_events, p=probabilities)
        
        
        time_delta = int(rand.integers(low=events[last_event]['time'][0], high=events[last_event]['time'][1]))
        timestamp = timestamp + timedelta(seconds=time_delta)
        
        eval(f'users[user_id].{next_event}(timestamp=timestamp)')
        n += 1