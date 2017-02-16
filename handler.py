import tornado.web


class APIBaseHandler(tornado.web.RequestHandler):
    '''
    Base handler with helpfull methods and initialization
    DO NOT use clas directly but instead extend and customize
    '''

    # def initialize(self, request_manager=None):
    #     self.request_manager = request_manager
    #     if self.request_manager is not None:
    #         self.request_manager.set_handler(self)

    def send_response(self, payload, statuscode):
        self.set_status(statuscode)
        self.write(payload)
        self.set_header('Content-Type', 'application/json')
        return

    def send_error_response(self, payload, statuscode=404):
        return self.send_response({"error": payload}, statuscode)

    def send_success_response(self, payload, statuscode=202):
        return self.send_response(payload, statuscode)

    def get(self):
        '''
        do not overwrite this method
        do your work in the doGet method of your subclass
        '''
        return self.do_get()
        try:
            return self.do_get()
        except Exception as e:
            return self.send_error_response(str(e))
