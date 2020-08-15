import geopandas
import pandas
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString, MultiPoint, MultiLineString
import scipy.special as sc
import numpy
from matplotlib.colors import ColorConverter, LinearSegmentedColormap


class coast_part():
    bbox = [] # xmin, ymin, xmax, ymax
    bbox_dict = {}
    real_bbox = [] # xmin, ymin, xmax, ymax
    real_bbox_dict = {}
    wave_spec = {
        'angle': 0, 
        'height': 0,
        'period': 0,
        'dang': 100
    }
    wind_spec = {
        'angle': 0, 
        'height': 0,
        'period': 0,
        'dang': 100
    }
    precision = 0
    coastline_geo = None
    waves_geo = None
    ocean_geo = None
    cmap = None


    def __init__(self, file_path, bbox):
        self.bbox = bbox
        self.bbox_dict = self.bbox2dict(bbox)
        self.coastline_geo = geopandas.read_file(file_path, bbox=bbox)
        self.cmap = LinearSegmentedColormap.from_list("", ["green","yellow","red"])


        # Getting the real bbox! It is much bigger than bbox
        xmin = bbox[0]
        xmax = bbox[2]
        ymin = bbox[1]
        ymax = bbox[3]

        for _, n, r in self.coastline_geo.itertuples(): 
            for pair in list(r.coords):
                if pair[0] > xmax:
                    xmax = pair[0]
                if pair[0] < xmin:
                    xmin = pair[0]
                if pair[1] > ymax:
                    ymax = pair[1]
                if pair[1] < ymin:
                    ymin = pair[1]

        self.real_bbox = (xmin, ymin, xmax, ymax)
        self.real_bbox_dict = self.bbox2dict(self.real_bbox)

    def bbox2dict(self, bbox):
        return {
            'xmin': bbox[0],
            'ymin': bbox[1],
            'xmax': bbox[2],
            'ymax': bbox[3],
        }

    # will be updated, works for the first quarter only 8()
    def wave_line(self, start_point):
        xmax = 0
        ymax = 0
        if (0 < self.wind_spec['angle'] < 90):
            xmax = self.bbox[2] # remake them to bbox_dict
            ymax = self.bbox[3]
        elif (90 < self.wind_spec['angle'] <= 180):
            xmax = self.bbox[0]
            ymax = self.bbox[3]
        elif (180 < self.wind_spec['angle'] < 270):
            xmax = self.bbox[0]
            ymax = self.bbox[1]
        elif (270 < self.wind_spec['angle'] <= 360):
            xmax = self.bbox[2]
            ymax = self.bbox[1]
        elif (self.wind_spec['angle'] == 90) or (self.wind_spec['angle'] == 270):
            # print([start_point, (start_point[0], self.bbox[3])])
            return [start_point, (start_point[0], self.bbox[3])]
        # print(start_point, xmax, ymax)
        end_point_x = xmax
        end_point_y = ((xmax - start_point[0]) * sc.tandg(self.wind_spec['angle'])) + start_point[1]
        if end_point_y > ymax:
            # print('Too big!')
            end_point_y = ymax
            end_point_x = ((ymax - start_point[1]) * sc.cotdg(self.wind_spec['angle'])) + start_point[0]
        # print(start_point, (end_point_x, end_point_y))
        return [start_point, (end_point_x, end_point_y)]

    def wave_parted(self, wave, intersect):
        # drawing parted line
        if intersect.type == 'Point':
            return {'waves': [LineString([wave.coords[0], intersect])], 'wave_dang': [self.wave_spec['dang']]}
        if intersect.type == 'MultiPoint':
            line_list = []
            # multilinestrings = []
            result_list = [] # colored lines
            line_list.append(wave.coords[0])
            line_list.extend([[point.x, point.y] for point in intersect])
            # if it is odd, than it ends on the ground
            if len(intersect) == 0:
                print('No intersect?')
                return {'waves': [], 'wave_dang': []}
            elif len(intersect) % 2 == 0:
                line_list.append(wave.coords[-1])
            # pair dots to lines!
            for pair in range(0, len(line_list), 2):
                result_list.append(LineString([line_list[pair], line_list[pair+1]]))
            # return list of wave LineStrings and their dangerously, wave_dang for the first one and 0 for others, 
            # because they are after ground.
            return {'waves': result_list, 'wave_dang': [0 if x>0 else self.wave_spec['dang'] for x in range(len(result_list))]} 

    def waves_set(self, angle=45, height=0, period=0):
        # Will be repaced by API call
        self.wave_spec = {
            'angle': angle, 
            'height': height,
            'period': period
        }
        # dangerousness should be calculated
        self.wave_spec['dang'] = 80

    def wind_set(self, angle=45, height=0, period=0):
        # Will be repaced by API call
        self.wind_spec = {
            'angle': angle, 
            'height': height,
            'period': period
        }
        # dangerousness should be calculated
        self.wind_spec['dang'] = 80

    # draw wave lines
    def wave_draw(self):
        self.waves_geo = geopandas.GeoDataFrame([], columns=['geometry'], crs="EPSG:4326")

        xstep = self.real_bbox_dict['xmin']
        ystep = self.real_bbox_dict['ymin']
        while True:
            self.waves_geo.loc[len(self.waves_geo), 'geometry'] = LineString(self.wave_line((xstep, self.real_bbox_dict['ymin'])))
            xstep += self.precision
            if xstep >= self.real_bbox_dict['xmax']:
                break
        while True:
            self.waves_geo.loc[len(self.waves_geo), 'geometry'] = LineString(self.wave_line((self.real_bbox_dict['xmin'], ystep)))
            ystep += self.precision
            if ystep >= self.real_bbox_dict['ymax']:
                break
        return self.waves_geo

    def ocean_draw(self):
        waves = self.wave_draw()

        # points of intersection
        intersection_list = []
        waves_intersected = {'waves': [], 'wave_dang': []}
        for _, fid, coastline in self.coastline_geo.itertuples():
            for _, wave in waves.itertuples():
                intersect = coastline.intersection(wave)
                # removing not intersected:
                if not intersect.is_empty:
                    intersection_list.append(intersect)
                    # drawing parted line
                    wave_parts = self.wave_parted(wave, intersect)
                    waves_intersected['waves'].extend(wave_parts['waves'])
                    waves_intersected['wave_dang'].extend(wave_parts['wave_dang'])
            
        # intersection_points = geopandas.GeoDataFrame(geometry=intersection_list)  # points of intercestion wave and coastline
        waves = geopandas.GeoDataFrame(waves_intersected['wave_dang'], geometry=waves_intersected['waves'], columns=['wave_dang'])
        # print(waves)

        # combined = geopandas.GeoDataFrame(pandas.concat([coast, waves], ignore_index=True)).plot()
        combined = geopandas.GeoDataFrame(pandas.concat([self.coastline_geo, waves], ignore_index=True))

        self.ocean_geo = combined
        return self.ocean_geo
        # print(combined)
        # coast.loc[len(coast), 'geometry'] = intersection

# print('bbox', bbox, 'real_bbox: ', (xmin, ymin), (xmax, ymax))

# add bboxes to plot
# combined.loc[len(coast), 'geometry'] = LineString([(bbox[0], bbox[1]), (bbox[2], bbox[1])])
# combined.loc[len(coast), 'geometry'] = LineString([(bbox[2], bbox[1]), (bbox[2], bbox[3])])
# combined.loc[len(coast), 'geometry'] = LineString([(bbox[2], bbox[3]), (bbox[0], bbox[3])])
# combined.loc[len(coast), 'geometry'] = LineString([(bbox[0], bbox[3]), (bbox[0], bbox[1])])

# combined.loc[len(coast), 'geometry'] = LineString([(real_bbox[0], real_bbox[1]), (real_bbox[2], real_bbox[1])])
# combined.loc[len(coast), 'geometry'] = LineString([(real_bbox[2], real_bbox[1]), (real_bbox[2], real_bbox[3])])
# combined.loc[len(coast), 'geometry'] = LineString([(real_bbox[2], real_bbox[3]), (real_bbox[0], real_bbox[3])])
# combined.loc[len(coast), 'geometry'] = LineString([(real_bbox[0], real_bbox[3]), (real_bbox[0], real_bbox[1])])


    def ocean_plot(self, precision=0.0001):
        self.precision = precision
        combined = self.ocean_draw()
        # Creating colormap
        norm=plt.Normalize(0,100)

        combined.plot(legend=True, column='wave_dang', cmap=self.cmap, missing_kwds = {'color': 'black', 'label': 'Coast line'})
        plt.show()



bbox = (-9.48859, 38.71225, -9.48369, 38.70596)
cascais = coast_part('/home/maksimpisarenko/tmp/osmcoast/coastlines-split-4326/lines.shp', bbox)
cascais.waves_set()
cascais.wind_set()
cascais.ocean_plot()