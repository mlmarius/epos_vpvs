# -*- coding: utf-8 -*-
from requestutils.request import Request
from requestutils.request_param import RequestParam
import requestutils.validators as v


class RequestManagerVPVS(object):

    def __init__(self):

        def dateFormatter(dtobj):
            return dtobj.isoformat()

        rq = Request()
        mintime = RequestParam('param_mintime',
                     name="UTC minimum date and time",
                     description='''UTC minimum date and time
                     meaning: data are extracted if related time is greater equal to mintime
                     standard reference:  ISO 8601 (YYYY-MM-DDThh:mm:ss.ccc)''',
                     validators=[v.ValidatorDateTimeRange('1970-01-01T00:00:00.000', 'now')]
                     )
        mintime.setOutputFormatter(dateFormatter)
        mintime.addTo(rq)

        maxtime = RequestParam('param_maxtime',
                     name="UTC maximum date and time",
                     description='''UTC maximum date and time
                     meaning: data are extracted if related time is less or equal to maxtime
                     standard reference:  ISO 8601 (YYYY-MM-DDThh:mm:ss.ccc)''',
                     validators=[v.ValidatorDateTimeRange('1970-01-01T00:00:00.000', 'now')]
                     )
        maxtime.setOutputFormatter(dateFormatter)
        maxtime.addTo(rq)

        # ensure mintime is smaller than maxtime
        rq.addPostValidator(v.ValidatorPostSmaller('param_mintime', 'param_maxtime'))

        #
        # Geographic region parameters
        #

        RequestParam('param_minlat',
                     name='Minimum latitude of the selection area',
                     description='''earthquakes and stations to calculate Vp/Vs are extracted if latitude is greater or equal to minlat
                     standard reference:  ISO 6709''',
                     validators=[v.ValidatorNumberRange(-90, 90)]
                     ).addTo(rq)

        RequestParam('param_maxlat',
                     name='Maximum latitude of the selection area',
                     description='''earthquakes and stations to calculate Vp/Vs are extracted if latitude is less or equal to maxlat
                     standard reference:  ISO 6709''',
                     validators=[v.ValidatorNumberRange(-90, 90)]
                     ).addTo(rq)

        rq.addPostValidator(v.ValidatorPostSmaller('param_minlat', 'param_maxlat'))

        RequestParam('param_minlon',
                     name='Minimum longitude of the selection area',
                     description='''earthquakes and stations to calculate Vp/Vs are extracted if longitude is greater or equal to minlon
                     standard reference:  ISO 6709''',
                     validators=[v.ValidatorNumberRange(-180, 180)]
                     ).addTo(rq)

        RequestParam('param_maxlon',
                     name='Maximum longitude of the selection area',
                     description='''earthquakes and stations to calculate Vp/Vs are extracted if longitude is less or equal to maxlon
                     standard reference:  ISO 6709''',
                     validators=[v.ValidatorNumberRange(-180, 180)]
                     ).addTo(rq)

        rq.addPostValidator(v.ValidatorPostSmaller('param_minlon', 'param_maxlon'))

        #
        # SPECIFIC PARAMS:
        # these parameters may are not mandatory but in this case they are set to NFO specifically chosen presets
        #

        # Earthquakes

        RequestParam('param_mineqdep',
                     name='Minimum depth of earthquakes',
                     description='''earthquakes to calculate Vp/Vs are extracted if depth is greater or equal to mineqdep
                     standard reference:  ISO 6709 negative a.s.l. positive b.s.l.''',
                     unit='km',
                     validators=[v.ValidatorNumberRange(-9.0, 6378.0)]
                     ).addTo(rq)

        RequestParam('param_maxeqdep',
                     name='Maximum depth of earthquakes',
                     description='''earthquakes to calculate Vp/Vs are extracted if depth is less or equal to mineqdep
                     standard reference:  ISO 6709 negative a.s.l. positive b.s.l.''',
                     unit='km',
                     validators=[v.ValidatorNumberRange(-9.0, 6378.0)]
                     ).addTo(rq)

        rq.addPostValidator(v.ValidatorPostSmaller('param_mineqdep', 'param_maxeqdep'))

        RequestParam('param_minnp',
                     name='Minimum number of P waves',
                     description='''number of p-waves onset observations
                     meaning: minimum number of p-waves onset observations, with quality hypoinverse standard weight less equal to maxpw, that one earthquake has to have to be extracted
                     standard reference: integer, no standard''',
                     default=1,
                     validators=[v.ValidatorInt(), v.ValidatorNumberMin(0)]
                     ).addTo(rq)

        RequestParam('param_minns',
                     name='Minimum number of S waves',
                     description='''number of s-waves onset observations
                     meaning: minimum number of s-waves onset observations, with quality hypoinverse standard weight less equal to maxsw, that one earthquake has to have to be extracted
                     standard reference: integer, no standard''',
                     default=1,
                     validators=[v.ValidatorInt(), v.ValidatorNumberMin(0)]
                     ).addTo(rq)

        RequestParam('param_maxpw',
                     name='quality hypoinverse standard weight',
                     description='''quality hypoinverse standard weight
                     meaning: maximum quality weight allowed for a p-wave reading so that it is counted for earthquake selection
                     standard reference: integer, hypoinverse 2000 standard (0 high quality, 3 worse, 4 not used)''',
                     validators=[v.ValidatorInt(), v.ValidatorNumberRange(0, 4)]
                     ).addTo(rq)

        RequestParam('param_maxsw',
                     name='quality hypoinverse standard weight',
                     description='''mum quality weight allowed for a s-wave reading so that it is counted for earthquake selection
                     standard reference: integer, hypoinverse 2000 standard (0 high quality, 3 worse, 4 not used)''',
                     validators=[v.ValidatorInt(), v.ValidatorNumberRange(0, 4)]
                     ).addTo(rq)

        RequestParam('param_minps',
                     name='number of P and S couples per earthquake',
                     description='''minimum number of p- and s-waves observed at one single station, with quality hypoinverse
                     standard weight less equal to maxpw and maxsw respectively, that one earthquake has to have to be extracted''',
                     validators=[v.ValidatorInt(), v.ValidatorNumberMin(0)]
                     ).addTo(rq)

        RequestParam('param_maxvpvspw',
                     name='',
                     description='',
                     default=3,
                     unit='',
                     validators=[v.ValidatorNumberRange(0, 4)]
                     ).addTo(rq)

        RequestParam('param_maxvpvssw',
                     name='',
                     description='',
                     default=3,
                     unit='',
                     validators=[v.ValidatorNumberRange(0, 4)]
                     ).addTo(rq)

        RequestParam('param_maxgap',
                     name='degrees of azimuthal stations distribution gap per earthquake',
                     description='''maximum allowed azimuthal gap so that a earthquakes is selected;
                     this parameters tends to guarantee a more feasible location and to exclude earthquakes
                     at the edge of the network coverage''',
                     validators=[v.ValidatorNumberRange(0, 360)]
                     ).addTo(rq)

        RequestParam('param_midi',
                     name='horizontal distance of the closest station from a earthquake',
                     description='''maximum distance of the closest station from an earthquake so that it
                     can be extracted, this parameters tends to guarantee a more feasible depth''',
                     unit='km',
                     default=40000,
                     validators=[v.ValidatorNumberRange(0, 40000)]
                     ).addTo(rq)

        RequestParam('param_maxherr',
                     name='maximum allowed formal horizontal error in earthquake location',
                     description='''the mean formal horizontal error directly given by
                     the location code or calculated as sqrt(errX²+errY*2) or from the uncertainty 2D or 3D ellipsoid parameters  (see the specific location code reference manual)''',
                     default=40000,
                     unit='km',
                     validators=[v.ValidatorNumberRange(0, 40000)]
                     ).addTo(rq)

        RequestParam('param_maxverr',
                     name='maximum allowed formal vertical error in earthquake location',
                     description='''is the mean formal vertical error directly given by the location code or calculated from the uncertainty 3D ellipsoid
                     parameters (see the specific location code reference manual)''',
                     default=6378,
                     unit='km',
                     validators=[v.ValidatorNumberRange(0, 6378)]
                     ).addTo(rq)
        
        RequestParam('param_maxvpvserr',
                     name='',
                     description='',
                     default=1000000,
                     unit='',
                     validators=[v.ValidatorNumberRange(0, 1000000000)]
                     ).addTo(rq)
                     
        RequestParam('param_DIV',
                     name='',
                     description='',
                     default=1000000,
                     unit='',
                     validators=[v.ValidatorNumberRange(1000000, 1000000)]
                     ).addTo(rq)
                     
        RequestParam('param_vpvsmin',
                     name='',
                     description='',
                     default=1.41,
                     unit='',
                     validators=[v.ValidatorNumberRange(1.41, 1.41)]
                     ).addTo(rq)

        RequestParam('param_modtype',
                     name='',
                     description='',
                     default=1,
                     unit='',
                     validators=[v.ValidatorNumberRange(1, 1)]
                     ).addTo(rq)

        RequestParam('param_codetype',
                     name='',
                     description='',
                     default=2,
                     unit='',
                     validators=[v.ValidatorNumberRange(2, 2)]
                     ).addTo(rq)

        RequestParam('param_mettype',
                     name='',
                     description='',
                     default=2,
                     unit='',
                     validators=[v.ValidatorNumberRange(2, 2)]
                     ).addTo(rq)

        self.rq = rq

    def bind(self, userargs):
        self.rq.bind(userargs)
        return self

    def validate(self):
        self.rq.validate()
        return self.rq
