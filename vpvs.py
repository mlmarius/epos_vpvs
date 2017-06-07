# -*- coding: utf-8 -*-
import handler
import tornado.ioloop
import tornado.web
import tornado.escape
from request_manager_vpvs import RequestManagerVPVS
import _mysql
import json
from ConfigParser import ConfigParser

class MainHandler(handler.APIBaseHandler):

    def initialize(self, config):
        self.config = config

    def do_get(self):
        manager = RequestManagerVPVS()
        user_request = manager.bind(self).validate()
        if user_request.is_valid:
            args = user_request.getArgs()

            # Uncomment lines 17, 18 in order to just show the user request args and stop
            # self.send_success_response(args)
            # return

            db = _mysql.connect(self.config.get('db','host'),
                                self.config.get('db','user'),
                                self.config.get('db','pass'),
                                self.config.get('db','db'))

            query = '''
                    select distinct
                    ( 1 + ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/{param_DIV}) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{param_DIV})) / (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{param_DIV})) as vpvs_value,
                           ( ( (pow(f.wei,2)*0.02 + pow(g.wei,2)*0.02) / ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/{param_DIV}) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{param_DIV})) ) + ((pow(f.wei,2)*0.02)/(TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{param_DIV}))) as vpvs_error,
                    c.origintime as event_origin_time,
                    h.lat as station_latitude,
                    h.lon as station_longitude,
                    h.elev as station_elevation,
                    h.network as network_code,
                    h.stacode as station_code,
                    h.loco as station_location,
                    f.pick as p_arrival_time,
                    f.wei as p_quality,
                    g.pick as s_arrival_time,
                    g.wei s_quality,
                    c.eqkID as event_id,
                    c.id as event_loc_id,
                    c.lat as event_latitude,
                    c.lon as event_longitude,
                    c.elev as event_elevation
                    from
                    (select c.eqkID as ID,count(*) as counterPS from phases f, phases g, eqlocations c, stations h where f.eqkID=g.eqkID and g.eqkID=c.eqkID and f.type='P' and g.type='S' and f.wei<={param_maxpw} and g.wei<={param_maxpw} and f.stacode=g.stacode and f.stacode=h.stacode and g.stacode=h.stacode and f.loco=h.loco and g.loco=h.loco and f.loco=g.loco and (h.lat between {param_minlat} and {param_maxlat}) and (h.lon between {param_minlon} and {param_maxlon}) and (h.elev between {param_mineqdep} and {param_maxeqdep}) and c.model={param_modtype} and c.lcode={param_codetype} and c.method={param_mettype} and (c.origintime between '{param_mintime}' and '{param_maxtime}') group by f.eqkID) as tblPS,

                    (select f.eqkID as ID,count(*) as counterP from phases f, eqlocations c where f.eqkID=c.eqkID and f.type='P' and f.wei<={param_maxpw} and c.model={param_modtype} and c.lcode={param_codetype} and c.method={param_mettype} and (c.origintime between '{param_mintime}' and '{param_maxtime}') group by f.eqkID) as tblP,
                    (select g.eqkID as ID,count(*) as counterS from phases g, eqlocations c where g.eqkID=c.eqkID and g.type='S' and g.wei<={param_maxsw} and c.model={param_modtype} and c.lcode={param_codetype} and c.method={param_mettype} and (c.origintime between '{param_mintime}' and '{param_maxtime}') group by g.eqkID) as tblS,
                    eqlocations c, eqstatistics d, magnitudes e, phases f, phases g, stations h
                    where
                        tblPS.counterPS >= {param_minps}
                    and tblP.counterP >= {param_minnp}
                    and tblS.counterS >= {param_minns}
                    and f.wei<= {param_maxvpvspw}
                    and g.wei<= {param_maxvpvssw}
                    and d.gap <= {param_maxgap}
                    and d.mindist <= {param_midi}
                    and (d.errh <= {param_maxherr} or sqrt(pow(d.errx,2)+pow(d.erry,2)) <= {param_maxherr})
                    and d.errv <= {param_maxverr}
                    and c.eqkID=tblPS.ID
                    and c.eqkID=tblP.ID
                    and c.eqkID=tblS.ID
                    and c.model=1
                    and c.lcode={param_codetype}
                    and c.method={param_mettype}
                    and (c.lat between {param_minlat} and {param_maxlat})
                    and (c.lon between {param_minlon} and {param_maxlon})
                    and (c.elev between {param_mineqdep} and {param_maxeqdep})
                    and c.id=d.idloc
                    and c.eqkID=e.eqkID
                    and e.idloc=c.id
                    and (c.origintime between '{param_mintime}' and '{param_maxtime}')
                    and f.eqkID=g.eqkID
                    and c.eqkID=f.eqkID
                    and f.eqkID=g.eqkID
                    and g.eqkID=c.eqkID
                    and f.type='P'
                    and g.type='S'
                    and f.stacode=h.stacode
                    and h.stacode=g.stacode
                    and f.stacode=g.stacode
                    and f.loco=h.loco
                    and h.loco=g.loco
                    and f.loco=g.loco
                    having (vpvs_value > {param_vpvsmin}) and vpvs_error <= {param_maxvpvserr}
                    order by c.origintime asc
                    limit 1000000;
                    '''.format(**args)

            # uncomment lines 75, 76 in order to echo the query to the screen and stop
            # self.send_success_response(query)
            # return

            db.query(query)
            rs = db.store_result()
            # self.send_success_response(json.dumps(dict(result=rs.fetch_row(maxrows=0, how=1))))
            # db.close()

            resp = self.render_string('response.json', result=json.dumps(rs.fetch_row(maxrows=0, how=1)))
            self.write(resp)
            self.set_header('Content-Type', 'application/json')
            return
        else:
            errors = [e.message for e in user_request.global_errors]
            errors.extend(["{0}: {1}".format(param.varname,error.message) for param,error in user_request.errors ])
            return self.send_error_response(errors)


class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        queries = []

        # add some example queries
        queries.append(dict(
            param_mintime='2001-01-01T00:00:00.000',
            param_maxtime='2000-01-01T00:00:00.000',
            param_minlat=30,          # -90, 90 and smaller than maxlat
            param_maxlat=50,          # -90, 90
            param_minlon=40,          # -180, 180 and smaller than maxlon
            param_maxlon=60,          # -180, 180
            param_mineqdep=-70,       # -6378, -9 and smaller than maxeqdep
            param_maxeqdep=-30,       # -6378, -9
            param_minnp=2,            # number of p waves, int, min: 0
            param_minns=3,            # number of s waves, int, min: 0
            param_maxpw=3,            # int, 0, 4
            param_maxsw=3,            # int, 0, 4
            param_minps=4,            # 0, +
            param_maxvpvspw=3,
            param_maxvpvssw=3,
            param_maxgap=150,         # azim gap 0, 360
            param_midi=70,            # horiz dist of closest sta
            param_maxherr=300,        # 0, 4000
            param_maxverr=200,         # 0, 6378
            param_maxvpvserr=1000000,
            param_DIV=1000000,
            param_vpvsmin = 1.41,
            param_modtype = 1,
            param_codetype = 2,
            param_mettype = 2
        ))


        queries.append(dict(
            param_mintime='2015-01-01T00:00:00.000',
            param_maxtime='2015-05-01T00:00:00.000',
            param_minlat=43.10,          # -90, 90 and smaller than maxlat
            param_maxlat=43.65,          # -90, 90
            param_minlon=12.10,          # -180, 180 and smaller than maxlon
            param_maxlon=12.65,          # -180, 180
            param_mineqdep=0.4,       # -9, 6378 and smaller than maxeqdep
            param_maxeqdep=1.2,       # -9, 6378
            param_minnp=2,            # number of p waves, int, min: 0
            param_minns=3,            # number of s waves, int, min: 0
            param_maxpw=3,            # int, 0, 4
            param_maxsw=3,            # int, 0, 4
            param_minps=4,            # 0, +
            param_maxvpvspw=3,
            param_maxvpvssw=3,
            param_maxgap=150,         # azim gap 0, 360
            param_midi=70,            # horiz dist of closest sta
            param_maxherr=300,        # 0, 4000
            param_maxverr=200,         # 0, 6378
            param_maxvpvserr=1000000,
            param_DIV=1000000,
            param_vpvsmin = 1.41,
            param_modtype = 1,
            param_codetype = 2,
            param_mettype = 2
        ))

        for idx, q in enumerate(queries):
            queries[idx] = '&'.join([ '{}={}'.format(k, v) for k, v in q.iteritems() ])
        # transform the queries into http query strings
        queries = ['/query?%s' % q for q in queries]

        manager = RequestManagerVPVS()

        self.render('index.html', queries=queries, manager=manager)

class DcatHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        self.config = config

    def get(self):

        def recurse(validator, vartype=None, type_tags=None, descriptions=None):

            if type_tags is None:
                type_tags = []

            if descriptions is None:
                descriptions = []

            # print validator
            try:
                if isinstance(validator, list):
                    results = [None, None, [], []]
                    for crt_validator in validator:
                        _, crt_vartype, crt_type_tags, crt_descriptions = recurse(crt_validator, vartype, type_tags, descriptions)
                        
                        if results[1] is None:
                            results[1] = crt_vartype

                        results[2].extend(crt_type_tags)
                        results[3].append(crt_validator.describe())

                    results[2] = set(results[2])
                    results[3] = set(results[3])
                    return results
            except TypeError as e:
                # print "not a list of validators"
                pass

            try:
                vartype = validator.type
            except AttributeError:
                # print "does not have validator.type"
                pass

            try:
                type_tags.extend(validator.type_tags)
                # print type_tags
            except AttributeError:
                # print "does not have validator.type_tags"
                pass


            try:
                # print "recursing to internal_validators"
                return recurse(validator.internal_validators, vartype, type_tags)
            except AttributeError as e:
                # print e
                # print "does not have internal_validators"
                return (validator, vartype, type_tags, [validator.describe()])


                

        manager = RequestManagerVPVS()

        param_descriptions = []
        for param in manager.rq.parameters:
            for validator in param.validators:
                validator_description = recurse(validator)
                # parameter name, parameter primitive type, validation tags, validator descriptions
                validation_hints = list(validator_description[2])
                if param.unit:
                    validation_hints.append('unit:{}'.format(param.unit))

                descriptions = list(validator_description[3])
                param_description = param.describe()
                if param_description:
                    param_description.strip()
                    descriptions.append(param_description)


                param_descriptions.append([param.varname, validator_description[1], validation_hints, descriptions])

        self.set_header("Content-Type", 'application/xml; charset="utf-8"')
        # self.set_header("Content-Disposition", "attachment; filename=dcat.xml")  
        self.render('dcat.xml', param_descriptions=param_descriptions)

if __name__ == "__main__":

    cfg = ConfigParser()
    cfg.read('config.ini')

    settings = dict(
        debug=True,
        template_path='templates/'
    )

    application = tornado.web.Application([
        (r"/", IndexHandler),
        (r"/query", MainHandler, dict(config=cfg)),
        (r"/dcat", DcatHandler, dict(config=cfg))
    ], **settings)
    application.listen(cfg.get('service', 'port'))
    tornado.ioloop.IOLoop.current().start()
