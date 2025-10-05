import requests

class StravaConnector:

    headers = []

    def __init__(self, access_token):
        self.access_token = access_token
        self.base_url = 'https://www.strava.com/api/v3'

    def fetch_activities(self, per_page=10):
        url = f"{self.base_url}/athlete/activities"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        params = {'per_page': per_page}
        response = requests.get(url, headers=headers, params=params)
        self.headers = response.headers

        return response.json()

    def fetch_activity_details(self, activity_id):
        url = f"{self.base_url}/activities/{activity_id}"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            # Handle error appropriately
            print(f"Error fetching activity {activity_id}: {response.status_code}")
            return None

    def fetch_activity_streams(self, activity_id, stream_types=None):
        url = f"{self.base_url}/activities/{activity_id}/streams"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        
        # Default stream types if none provided
        if stream_types is None:
            stream_types = ['time', 'latlng', 'altitude', 'velocity_smooth']
        
        params = {'keys': ','.join(stream_types), 'key_by_type': True}
        response = requests.get(url, headers=headers, params=params)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching streams for activity {activity_id}: {response.status_code}")
            return None

    def fetch_activities_with_details(self, per_page=10):
        # First get basic activities
        activities = self.fetch_activities(per_page)
        
        # Then enrich with detailed information
        enriched_activities = []
        for activity in activities:
            # Get detailed activity info
            detailed_info = self.fetch_activity_details(activity['id'])
            
            if detailed_info:
                # Merge basic and detailed info
                enriched_activity = {**activity, **detailed_info}
                
                # Add streams data if available
                streams = self.fetch_activity_streams(activity['id'])
                if streams:
                    enriched_activity['streams'] = streams
                    
                enriched_activities.append(enriched_activity)
            else:
                # If we can't get detailed info, just add the basic activity
                enriched_activities.append(activity)
        
        return enriched_activities

    def fetch_activity_zones(self, activity_id):
        url = f"{self.base_url}/activities/{activity_id}/zones"
        headers = {'Authorization': f'Bearer {self.access_token}'}
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching zones for activity {activity_id}: {response.status_code}")
            return None


    def get_rate_limit(self):
        return {'usage': self.headers['x-ratelimit-usage'], 'limit': self.headers['x-ratelimit-limit']}