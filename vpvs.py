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
                                self.config.get('db','password'),
                                self.config.get('db','db'))

            query = '''
                    select distinct
                    ( 1 + ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/100000) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/100000)) / (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/100000)) as vpvs,
                    ( ( (pow(f.wei,2)*0.02 + pow(g.wei,2)*0.02) / ((TIMESTAMPDIFF(microsecond,c.origintime,g.pick)/100000) - (TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/100000)) ) + ((pow(f.wei,2)*0.02)/(TIMESTAMPDIFF(microsecond,c.origintime,f.pick)/100000))) as err,
                    c.origintime,h.lat,h.lon,h.elev,h.stacode,h.loco,f.type,f.pick,f.wei,g.type,g.pick,g.wei,c.id,c.lat,c.lon,c.elev
                    from
                    (select c.eqkid as ID,count(*) as counterPS from phases f, phases g, eqlocations c, stazioni h where f.eqkid=g.eqkid and g.eqkid=c.eqkid and f.type='P' and g.type='S' and f.wei<=4 and g.wei<=4 and f.stacode=g.stacode and f.stacode=h.stacode and g.stacode=h.stacode and f.loco=h.loco and g.loco=h.loco and f.loco=g.loco and (h.lat between {minlat} and {maxlat}) and (h.lon between {minlon} and {maxlon}) and (h.elev between 0 and 15) and c.model=1 and c.lcode=2 and c.method=2 and (c.origintime between '{mintime}' and '{maxtime}') group by f.eqkid) as tblPS,
                    (select f.eqkid as ID,count(*) as counterP from phases f, eqlocations c where f.eqkid=c.eqkid and f.type='P' and f.wei<=4 and c.model=1 and c.lcode=2 and c.method=2 and (c.origintime between '{mintime}' and '{maxtime}') group by f.eqkid) as tblP,
                    (select g.eqkid as ID,count(*) as counterS from phases g, eqlocations c where g.eqkid=c.eqkid and g.type='S' and g.wei<=4 and c.model=1 and c.lcode=2 and c.method=2 and (c.origintime between '{mintime}' and '{maxtime}') group by g.eqkid) as tblS,
                    eqlocations c, eqstatistics d, magnitudes e, phases f, phases g, stazioni h
                    where
                    tblPS.counterPS >= 1
                    and tblP.counterP >= 1
                    and tblS.counterS >= 1
                    and f.wei<= 4
                    and g.wei<= 4
                    and d.gap <= 360
                    and d.mindist <= 40000
                    and (d.errh <= 40000 or sqrt(pow(d.errx,2)+pow(d.erry,2)) <= 40000)
                    and d.errv <= 6378
                    and c.eqkid=tblPS.ID
                    and c.eqkid=tblP.ID
                    and c.eqkid=tblS.ID
                    and c.model=1
                    and (c.lat between {minlat} and {maxlat})
                    and (c.lon between {minlon} and {maxlon})
                    and (c.elev between 0 and 15)
                    and c.id=d.idloc
                    and c.eqkid=e.eqkid
                    and (c.origintime between '{mintime}' and '{maxtime}')
                    and f.eqkid=g.eqkid
                    and c.eqkid=f.eqkid
                    and f.eqkid=g.eqkid
                    and g.eqkid=c.eqkid
                    and f.type='P'
                    and g.type='S'
                    and f.stacode=h.stacode
                    and h.stacode=g.stacode
                    and f.stacode=g.stacode
                    and f.loco=h.loco
                    and h.loco=g.loco
                    and f.loco=g.loco
                    having (vpvs > 1.4) and err <= 1000000
                    order by c.origintime asc
                    limit 10000000;
                    '''.format(**args)

            # uncomment lines 75, 76 in order to echo the query to the screen and stop
            # self.send_success_response(query)
            # return

            db.query(query)
            rs = db.store_result()
            self.send_success_response(json.dumps(dict(result=rs.fetch_row(maxrows=0, how=1))))
            db.close()
            return
        else:
            errors = [e.message for e in user_request.global_errors]
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
            maxgap=150,         # azim gap 0, 360
            midi=70,            # horiz dist of closest sta
            maxherr=300,        # 0, 4000
            maxverr=200         # 0, 6378
        ))


        queries.append(dict(
            mintime='2010-04-01T00:00:00.000',
            maxtime='2010-05-01T00:00:00.000',
            minlat=43.10,          # -90, 90 and smaller than maxlat
            maxlat=43.65,          # -90, 90
            minlon=12.10,          # -180, 180 and smaller than maxlon
            maxlon=12.65,          # -180, 180
            mineqdep=-70,       # -6378, -9 and smaller than maxeqdep
            maxeqdep=-30,       # -6378, -9
            minnp=2,            # number of p waves, int, min: 0
            minns=3,            # number of s waves, int, min: 0
            maxpw=3,            # int, 0, 4
            maxsw=3,            # int, 0, 4
            minps=4,            # 0, +
            maxgap=150,         # azim gap 0, 360
            midi=70,            # horiz dist of closest sta
            maxherr=300,        # 0, 4000
            maxverr=200         # 0, 6378
        ))

        for idx, q in enumerate(queries):
            queries[idx] = '&'.join([ '{}={}'.format(k, v) for k, v in q.iteritems() ])
        # transform the queries into http query strings
        queries = ['/query?%s' % q for q in queries]

        manager = RequestManagerVPVS()

        self.render('vpvs_index.html', queries=queries, manager=manager)

if __name__ == "__main__":

    cfg = ConfigParser()
    cfg.read('config.ini')

    settings = dict(
        debug=True,
        template_path='templates/'
    )

    application = tornado.web.Application([
        (r"/", IndexHandler),
        (r"/query", MainHandler, dict(config=cfg))
    ], **settings)
    application.listen(8888)
    tornado.ioloop.IOLoop.current().start()
