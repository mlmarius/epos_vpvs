# -*- coding: utf-8 -*-
import handler
import tornado.ioloop
import tornado.web
import tornado.escape
from request_manager_vpvs import RequestManagerVPVS
import _mysql
import json
from ConfigParser import ConfigParser, NoSectionError
import os


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

            db = _mysql.connect(self.config.get('db', 'host'),
                                self.config.get('db', 'user'),
                                self.config.get('db', 'pass'),
                                self.config.get('db', 'db'))

            query = '''
                    select distinct
                    ( 1 + ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/{DIV}) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{DIV})) / (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{DIV})) as vpvs_value,
                           ( ( (pow(f.wei,2)*0.02 + pow(g.wei,2)*0.02) / ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/{DIV}) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{DIV})) ) + ((pow(f.wei,2)*0.02)/(TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/{DIV}))) as vpvs_error,
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
                    (select c.eqkID as ID,count(*) as counterPS from phases f, phases g, eqlocations c, stations h where f.eqkID=g.eqkID and g.eqkID=c.eqkID and f.type='P' and g.type='S' and f.wei<={maxpw} and g.wei<={maxpw} and f.stacode=g.stacode and f.stacode=h.stacode and g.stacode=h.stacode and f.loco=h.loco and g.loco=h.loco and f.loco=g.loco and (h.lat between {minlat} and {maxlat}) and (h.lon between {minlon} and {maxlon}) and (h.elev between {mineqdep} and {maxeqdep}) and c.model={modtype} and c.lcode={codetype} and c.method={mettype} and (c.origintime between '{mintime}' and '{maxtime}') group by f.eqkID) as tblPS,

                    (select f.eqkID as ID,count(*) as counterP from phases f, eqlocations c where f.eqkID=c.eqkID and f.type='P' and f.wei<={maxpw} and c.model={modtype} and c.lcode={codetype} and c.method={mettype} and (c.origintime between '{mintime}' and '{maxtime}') group by f.eqkID) as tblP,
                    (select g.eqkID as ID,count(*) as counterS from phases g, eqlocations c where g.eqkID=c.eqkID and g.type='S' and g.wei<={maxsw} and c.model={modtype} and c.lcode={codetype} and c.method={mettype} and (c.origintime between '{mintime}' and '{maxtime}') group by g.eqkID) as tblS,
                    eqlocations c, eqstatistics d, magnitudes e, phases f, phases g, stations h
                    where
                        tblPS.counterPS >= {minps}
                    and tblP.counterP >= {minnp}
                    and tblS.counterS >= {minns}
                    and f.wei<= {maxvpvspw}
                    and g.wei<= {maxvpvssw}
                    and d.gap <= {maxgap}
                    and d.mindist <= {midi}
                    and (d.errh <= {maxherr} or sqrt(pow(d.errx,2)+pow(d.erry,2)) <= {maxherr})
                    and d.errv <= {maxverr}
                    and c.eqkID=tblPS.ID
                    and c.eqkID=tblP.ID
                    and c.eqkID=tblS.ID
                    and c.model=1
                    and c.lcode={codetype}
                    and c.method={mettype}
                    and (c.lat between {minlat} and {maxlat})
                    and (c.lon between {minlon} and {maxlon})
                    and (c.elev between {mineqdep} and {maxeqdep})
                    and c.id=d.idloc
                    and c.eqkID=e.eqkID
                    and e.idloc=c.id
                    and (c.origintime between '{mintime}' and '{maxtime}')
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
                    having (vpvs_value > {vpvsmin}) and vpvs_error <= {maxvpvserr}
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

            resp = self.render_string(
                'response.json', result=json.dumps(rs.fetch_row(maxrows=0, how=1)))
            self.write(resp)
            self.set_header('Content-Type', 'application/json')
            return
        else:
            errors = [e.message for e in user_request.global_errors]
            errors.extend(["{0}: {1}".format(param.varname, error.message)
                           for param, error in user_request.errors])
            return self.send_error_response(errors)


class IndexHandler(tornado.web.RequestHandler):

    def get(self):
        queries = []

        # add some example queries
        queries.append(dict(
            mintime='2001-01-01T00:00:00.000',
            maxtime='2000-01-01T00:00:00.000',
            minlat=30,          # -90, 90 and smaller than maxlat
            maxlat=50,          # -90, 90
            minlon=40,          # -180, 180 and smaller than maxlon
            maxlon=60,          # -180, 180
            mineqdep=-70,       # -6378, -9 and smaller than maxeqdep
            maxeqdep=-30,       # -6378, -9
            minnp=2,            # number of p waves, int, min: 0
            minns=3,            # number of s waves, int, min: 0
            maxpw=3,            # int, 0, 4
            maxsw=3,            # int, 0, 4
            minps=4,            # 0, +
            maxvpvspw=3,
            maxvpvssw=3,
            maxgap=150,         # azim gap 0, 360
            midi=70,            # horiz dist of closest sta
            maxherr=300,        # 0, 4000
            maxverr=200,         # 0, 6378
            maxvpvserr=1000000,
            DIV=1000000,
            vpvsmin=1.41,
            modtype=1,
            codetype=2,
            mettype=2
        ))

        queries.append(dict(
            mintime='2015-01-01T00:00:00.000',
            maxtime='2015-05-01T00:00:00.000',
            minlat=43.10,          # -90, 90 and smaller than maxlat
            maxlat=43.65,          # -90, 90
            minlon=12.10,          # -180, 180 and smaller than maxlon
            maxlon=12.65,          # -180, 180
            mineqdep=0.4,       # -9, 6378 and smaller than maxeqdep
            maxeqdep=1.2,       # -9, 6378
            minnp=2,            # number of p waves, int, min: 0
            minns=3,            # number of s waves, int, min: 0
            maxpw=3,            # int, 0, 4
            maxsw=3,            # int, 0, 4
            minps=4,            # 0, +
            maxvpvspw=3,
            maxvpvssw=3,
            maxgap=150,         # azim gap 0, 360
            midi=70,            # horiz dist of closest sta
            maxherr=300,        # 0, 4000
            maxverr=200,         # 0, 6378
            maxvpvserr=1000000,
            DIV=1000000,
            vpvsmin=1.41,
            modtype=1,
            codetype=2,
            mettype=2
        ))

        for idx, q in enumerate(queries):
            queries[idx] = '&'.join(['{}={}'.format(k, v)
                                     for k, v in q.iteritems()])
        # transform the queries into http query strings
        queries = ['/query?%s' % q for q in queries]

        manager = RequestManagerVPVS()

        self.render('index.html', queries=queries, manager=manager)


class DcatHandler(handler.APIBaseHandler):

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
                        _, crt_vartype, crt_type_tags, crt_descriptions = recurse(
                            crt_validator, vartype, type_tags, descriptions)

                        if results[1] is None:
                            results[1] = crt_vartype

                        results[2].extend(crt_type_tags)
                        results[3].append(crt_validator.describe())

                    results[2] = set(results[2])
                    results[3] = set(results[3])
                    return results
            except TypeError:
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
            except AttributeError:
                # print e
                # print "does not have internal_validators"
                return (validator, vartype, type_tags, [validator.describe()])

        manager = RequestManagerVPVS()

        descriptions = []
        for param in manager.rq.parameters:
            for validator in param.validators:
                validator_description = recurse(validator)
                # parameter name, parameter primitive type, validation tags,
                # validator descriptions
                validation_hints = list(validator_description[2])
                if param.unit:
                    validation_hints.append('unit:{}'.format(param.unit))

                descriptions = list(validator_description[3])
                description = param.describe()
                if description:
                    description.strip()
                    descriptions.append(description)

                descriptions.append([param.varname, validator_description[
                                          1], validation_hints, descriptions])

        self.set_header("Content-Type", 'application/xml; charset="utf-8"')
        # self.set_header("Content-Disposition", "attachment; filename=dcat.xml")
        try:
            self.render('dcat.xml', descriptions=descriptions)
        except IOError:
            self.send_error_response(
                'Please move dcat.sample.xml to dcat.xml and customise.')

if __name__ == "__main__":

    cfg = ConfigParser()
    cfg.read('config.ini')

    # if environment configuration is present then override whatever there is
    # usefull for overriding configuration in Docker mode
    # environment variables should look like this EP_SECTIONNAME_VARNAME_HERE='value'

    # EP_DB_HOST=<ip or hostname of database>
    # EP_DB_USER=<username of db>
    # EP_DB_PASS=<password to the database>
    # EP_DB_DB=<name of database>
    # EP_SERVICE_PORT=<port on which the app is running>

    env_config = {key[3:].lower(): val for key, val in os.environ.items() if key.startswith('EP_')}
    for k, v in env_config.items():
        keyparts = k.split('_')
        sectionname = keyparts[0]
        varname = '_'.join(keyparts[1:])

        try:
            cfg.set(sectionname, varname, v)
        except NoSectionError:
            cfg.add_section(sectionname)
            cfg.set(sectionname, varname, v)

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
