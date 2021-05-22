from datetime import datetime, timedelta
import numpy as np

from google.cloud import storage
from google.cloud import bigquery

import sys
import os

bigquery_client = bigquery.Client.from_service_account_json('../../credentials/data-analysis-sql-309220-6ce084250abd.json')



users = dict()
items = dict()



class Item:
    def __init__(self, item_id, category, price, quantity):
        self.item_id = item_id
        self.category = category
        self.price = price
        self.quantity = quantity
        



class User:    
    def __init__(self, name, user_id):
        self.name = name
        self.user_id = user_id
        self.registered = False
        self.session_events = []
        self.last_properties = dict()
    

    def add_data(self, properties=None):
        if properties is None:
            properties = self.last_properties
        else:
            for k in self.last_properties.keys():
                properties[k] = self.last_properties[k]
        
        event_data = {
            'user_id': self.user_id,
            'event_name': self.last_event,
            'timestamp': self.last_activity.strftime('%Y-%m-%d %H:%M:%S.%f'),
            'properties': properties
        }

        self.session_events.append(event_data)
    
    
    
    @property
    def visit_probability(self):
        """Calculate visit_probability as combination of initial probability and satisfaction level and other factor.
        """
        p = 0.01 + self.satisfaction / 1000
        
        if p < 0:
            p = 0
        elif p > 0.1:
            p = 0.1

        return p / 86400
    
    
    
    @property
    def satisfaction(self):
        """Calculate user satisfaction level.
        """
        satisfaction = 0
        
        if self.registered:
            satisfaction += satisfaction_impact['registration']

        if hasattr(self, 'n_purchases'):
            satisfaction += self.n_purchases * satisfaction_impact['purchase']  

        if hasattr(self, 'item_views'):
            satisfaction += self.item_views * satisfaction_impact['item_view'] 
            
        if hasattr(self, 'searches'):
            satisfaction += self.searches * satisfaction_impact['search'] 
        
        return satisfaction

        
    
    @property
    def items_in_basket(self):
        """Calculate items in basket
        """
        return len(self.basket) if hasattr(self, 'basket') else 0

    

    @property
    def n_items_in_basket(self):
        """Calculate number of deleted items
        """
        return len(self.basket) if hasattr(self, 'basket') else 0     

 

    @property
    def n_purchases(self):
        """Calculate number of purchased items
        """
        return len(self.purchased_items) if hasattr(self, 'purchased_items') else 0 
    

    
    def visit(self, timestamp, platform, country):
        """User visit event. 
        It's the first touch with the app within a session.
        Event creates / updates user attributes:
            visits: number of visits.
            last_visit: time of the last visit.
            last_activity: time of the last activity.
            last_properties: properties like platform and country.
        
        Parameters:
            timestamp: time of the event.
        """
        self.active_session = True
        self.last_event = 'visit'
        self.last_activity = timestamp
        self.visits = self.visits + 1 if hasattr(self, 'visits') else 1
        self.last_visit = timestamp
        
        self.last_properties = {
            'platform': platform,
            'country': country
        }
        
        self.add_data()
        print(self.last_event, timestamp)


    
    def create_account(self, timestamp):
        """User creates an account. 
        Parameters:
            timestamp: time of the event.
        """
        self.last_event = 'create_account'
        self.last_activity = timestamp
        self.registered = True
        self.registration_date = timestamp
        
        self.add_data()
        print(self.last_event, timestamp)
            
    
    
    def search(self, timestamp):
        """User performs a search. 
        Parameters:
            timestamp: time of the event.
        """
        self.last_event = 'search'
        self.searches = self.searches + 1 if hasattr(self, 'searches') else 1
        self.last_activity = timestamp
        
        rand = np.random.default_rng(seed=abs(hash(timestamp)))
        self.available_items = rand.choice(a=list(items.keys()), size=10 if len(items.keys())>=10 else len(items.keys()), replace=False)

        self.add_data()
        print(self.last_event, timestamp)
        
    
        
    def view_item(self, timestamp):
        """User views an item. 
        Parameters:
            timestamp: time of the event.
        """  
        self.last_event = 'view_item'
        self.last_activity = timestamp
        self.item_views = self.item_views + 1 if hasattr(self, 'item_views') else 1
        
        rand = np.random.default_rng(seed=abs(hash(timestamp)))
        item_id = rand.choice(a=self.available_items)
        self.last_open_item = item_id
        items[item_id].views = items[item_id].views + 1 if hasattr(items[item_id], 'views') else 1

        properties = {'item_id': item_id} 
        self.add_data(properties=properties)
        print(self.last_event, timestamp)
    
    
    
    def add_to_basket(self, timestamp):
        """User adds an item to the basket. 
        Parameters:
            timestamp: time of the event.
        """
        self.last_event = 'add_to_basket'
        self.last_activity = timestamp
        
        if hasattr(self, 'basket'):
            self.basket.append(self.last_open_item)
        else:
            self.basket = [self.last_open_item]

        properties = {'item_id': self.last_open_item} 
        self.add_data(properties=properties)
        print(self.last_event, timestamp)

        
        
    def open_basket(self, timestamp):
        """User adds an item to the basket. 
        Parameters:
            timestamp: time of the event.
        """
        self.last_event = 'open_basket'
        self.last_activity = timestamp
        
        self.add_data()
        print(self.last_event, timestamp)
        
        
    
    def remove_from_basket(self, timestamp):
        """User removes an item to the basket. 
        Parameters:
            timestamp: time of the event.
        """
        self.last_event = 'remove_from_basket'
        self.last_activity = timestamp
        
        rand = np.random.default_rng(seed=abs(hash(timestamp)))
        item_id = rand.choice(a=self.basket)
        self.basket.remove(item_id)
        
        properties = {'item_id': item_id} 
        self.add_data(properties=properties)
        print(self.last_event, timestamp)
        
    
    
    def pay(self, timestamp):
        """User pays for item / set of items. 
        Parameters:
            item_id: id of the item user views.
            timestamp: time of the event.
        """
        self.last_event = 'pay'
        self.last_activity = timestamp
        
        for item_id in self.basket:  
            # updateitems attributes
            items[item_id].quantity = items[item_id].quantity - 1
        
        # update buyer's attributes
        if hasattr(self, 'purchased_items'):
            self.purchased_items.extend(self.basket)
        else:
            self.purchased_items = self.basket
        
        properties = {'item_ids': ','.join(self.basket)} 
        self.add_data(properties=properties)
        
        # empy basket
        self.basket = []
        print(self.last_event, timestamp)

        
    
    def do_nothing(self, timestamp):
        self.active_session = False
        
        bq_error = bigquery_client.insert_rows_json('data-analysis-sql-309220.synthetic.marketplace', self.session_events)
        if bq_error != []:
            print(bq_error) 

        self.session_events = []
        