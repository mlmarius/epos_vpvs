# -*- coding: utf-8 -*-
import handler
import tornado.ioloop
import tornado.web
import tornado.escape
from request_manager_vpvs import RequestManagerVPVS
import _mysql
import json
from ConfigParser import ConfigParser
from dateutil import parser
from obspy.geodetics.base import gps2dist_azimuth as distaz

from tornado.concurrent import run_on_executor
# `pip install futures` for python2
from concurrent.futures import ThreadPoolExecutor
# from concurrent.futures import ProcessPoolExecutor

MAX_WORKERS = 8


class MainHandler(handler.APIBaseHandler):
    executor = ThreadPoolExecutor(max_workers=MAX_WORKERS)
    # executor = ProcessPoolExecutor(max_workers=MAX_WORKERS)

    def initialize(self, config):
        self.config = config

    @run_on_executor
    def do_query(self, user_request):
        print "do_query(): start"
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

        # self.send_success_response(query)
        # return

        db.query(query)
        rs = db.store_result()
        # self.send_success_response(json.dumps(dict(result=rs.fetch_row(maxrows=0, how=1))))
        # db.close()
        print "do_query(): now returning result"
        return rs

    @tornado.gen.coroutine
    def do_get(self):
        print "do_get(): start"
        manager = RequestManagerVPVS()
        user_request = manager.bind(self).validate()
        if user_request.is_valid:
            as_plot = user_request.getParam('as_plot').getValue()
            rs = yield self.do_query(user_request)

            if as_plot is False:
                print "do_get(): got result from do_query()"
                resp = self.render_string(
                    'response.json', result=json.dumps(rs.fetch_row(maxrows=0, how=1)))
                self.write(resp)
                self.set_header('Content-Type', 'application/json')
                print "do_get(): response sent"
                return

            # user requested the data to be sent back as plot
            result = self.do_plot(rs.fetch_row(maxrows=0, how=1))
        else:
            errors = [e.message for e in user_request.global_errors]
            errors.extend(["{0}: {1}".format(param.varname, error.message)
                           for param, error in user_request.errors])
            self.send_error_response(errors)

    def do_plot(self, data, request):

        allo = {}
        for d in data:
            vpvs = d['vpvs_value']
            errs = d['vpvs_error']
            otim = parser.parse(d['event_origin_time'])
            elat = d['event_latitude']
            elon = d['event_longitude']
            edep = d['event_elevation']
            slat = d['station_latitude']
            slon = d['station_longitude']
            sele = d['station_elevation']
            scod = d['station_code'] + '_' + \
                d['station_location'] + '_' + d['network_code']
            dis, azi, baz = distaz(float(elat), float(
                elon), float(slat), float(slon))
            test = False
            if float(dis) <= maxdist * 1000 and float(edep) >= mindepth and float(edep) <= maxdepth:
                dis = str(float(dis) / 1000)
                for key in allo.keys():
                    if key == scod:
                        test = True
                        pippo = []
                        pippo = allo[key]
                        pippo.append(
                            [otim, vpvs, errs, dis, azi, baz, slat, slon, sele])
                        allo.update({scod: pippo})
                if not test:
                    allo.update(
                        {scod: [[otim, vpvs, errs, dis, azi, baz, slat, slon, sele]]})

        #######################################################################
        ######### Producing Plot ##############################################
        for key in allo.keys():
            times = list(map(itemgetter(0),  allo[key]))
            if len(times) >= 5 * mindat:
                values = np.asarray(
                    map(float, list(map(itemgetter(1),  allo[key]))))
                errors = np.asarray(
                    map(float, list(map(itemgetter(2),  allo[key]))))
                distances = list(map(itemgetter(3),  allo[key]))
                azimuths = list(map(itemgetter(4),  allo[key]))
                bazimuths = list(map(itemgetter(5),  allo[key]))
                zippo_val = pandas.rolling_mean(values, mindat)
                zippo_std = pandas.rolling_std(values, mindat)

                x = list(times[mindat - 1:-1])
                y = list(zippo_val[mindat - 1:-1])
                e = list(zippo_std[mindat - 1:-1])
                # plot
                plt.title("Vp/Vs Time Series at " +
                          nfoname + " NFO Station " + key)
                plt.plot(x, y)
                plt.plot(x, y, 'bo')
                plt.errorbar(x, y, yerr=e, fmt='o')
                # beautify the x-labels
                plt.gcf().autofmt_xdate()
                plt.ylabel('Vp/Vs Ratio')
                plt.xlabel('Date Time')

                plt.show()
                fig = plt.figure()
                figname = key + ".png"
                fig.savefig(figname)
            else:
                print "Cannot Plot " + key + ": too few data"


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

        # this works on the NIEP database
        queries.append(dict(
            minnp=2,
            vpvsmin=1.41,
            codetype=2,
            minlon=19,
            maxgap=150,
            mintime='2017-01-01T00:00:00.000',
            maxverr=200,
            modtype=1,
            minlat=42,
            maxlon=30,
            midi=70,
            maxvpvserr=1000000,
            mineqdep=0.0,
            DIV=1000000,
            maxsw=4,
            minns=3,
            maxvpvssw=4,
            maxlat=48,
            minps=4,
            maxeqdep=200,
            mettype=2,
            maxtime='2017-05-01T00:00:00.000',
            maxherr=300,
            maxvpvspw=4,
            maxpw=4
        ))

        # this works on the NIEP database and produce a plot
        queries.append(dict(
            minnp=2,
            vpvsmin=1.41,
            codetype=2,
            minlon=19,
            maxgap=150,
            mintime='2017-01-01T00:00:00.000',
            maxverr=200,
            modtype=1,
            minlat=42,
            maxlon=30,
            midi=70,
            maxvpvserr=1000000,
            mineqdep=0.0,
            DIV=1000000,
            maxsw=4,
            minns=3,
            maxvpvssw=4,
            maxlat=48,
            minps=4,
            maxeqdep=200,
            mettype=2,
            maxtime='2017-05-01T00:00:00.000',
            maxherr=300,
            maxvpvspw=4,
            maxpw=4,
            as_plot=1
        ))

        for idx, q in enumerate(queries):
            queries[idx] = '&'.join(['{}={}'.format(k, v)
                                     for k, v in q.iteritems()])
        # transform the queries into http query strings
        queries = ['/query?%s' % q for q in queries]

        manager = RequestManagerVPVS()

        self.render('index.html', queries=queries, manager=manager)


class DcatHandler(tornado.web.RequestHandler):

    def initialize(self, config):
        self.config = config

    def get(self):

        def recurse(validator, vartype=None, type_tags=None, descriptions=None):
            """Extract all validator information from the request."""
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

        param_descriptions = []
        for param in manager.rq.parameters:
            for validator in param.validators:
                validator_description = recurse(validator)
                # parameter name, parameter primitive type, validation tags,
                # validator descriptions
                validation_hints = list(validator_description[2])
                if param.unit:
                    validation_hints.append('unit:{}'.format(param.unit))

                descriptions = list(validator_description[3])
                param_description = param.describe()
                if param_description:
                    param_description.strip()
                    descriptions.append(param_description)

                param_descriptions.append([param.varname, validator_description[
                                          1], validation_hints, descriptions])

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

    def foo():
        import datetime
        print "{} tornado loop is runing...".format(datetime.datetime.now())

    tornado.ioloop.PeriodicCallback(foo, 1000).start()
    tornado.ioloop.IOLoop.current().start()
