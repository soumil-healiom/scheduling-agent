import falcon
import json

class ScheduleVisitResource:
    def on_post(self, req, resp):
        data = json.load(req.bounded_stream)
        response = {
            "status": "success",
            "message": f"Appointment scheduled for {data['first name']} {data['last name']} on {data['date']} at {data['time_start']}",
            "data_received": data
        }
        resp.media = response

class RescheduleVisitResource:
    def on_post(self, req, resp):
        data = json.load(req.bounded_stream)
        response = {
            "status": "success",
            "message": f"Appointment rescheduled for {data['first name']} {data['last name']} to {data['new_date']}",
            "data_received": data
        }
        resp.media = response

app = falcon.App()

app.add_route('/api.healion.com/practice_mgmt/schedule', ScheduleVisitResource())

app.add_route('/api.healion.com/practice_mgmt/reschedule', RescheduleVisitResource())

if __name__ == '__main__':
    from wsgiref import simple_server
    httpd = simple_server.make_server('127.0.0.1', 8000, app)
    print('Serving on http://127.0.0.1:8000')
    httpd.serve_forever()
