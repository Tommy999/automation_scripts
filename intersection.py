# -*- coding: utf-8 -*-
import os, sys
import time
import math
import arcpy


class Profiler(object):
    def __enter__(self):
        self._startTime = time.time()

    def __exit__(self, type, value, traceback):
        print "\t\tElapsed time: {:.3f} sec".format(time.time() - self._startTime)


def calculate_middle(point1, point2):

    xmid = (point1[0] + point2[0])/2
    ymid = (point1[1]+point2[1])/2
    return [xmid, ymid]


def get_azimuth_polyline(point1, point2):
    try:
        radian = math.atan((point2[0] -point1[0])/(point2[1] - point1[1]))
    except ZeroDivisionError:
        degrees = 90
        return degrees
    degrees = radian * 180 / math.pi
    return degrees


def project_point(point1, point2):

    point_WGS1 = arcpy.Point(point1[0], point1[1])
    point_WGS2 = arcpy.Point(point2[0], point2[1])
    pg1 = arcpy.PointGeometry(point_WGS1, arcpy.SpatialReference(4326)).projectAs(arcpy.SpatialReference(32641))
    pg2 = arcpy.PointGeometry(point_WGS2, arcpy.SpatialReference(4326)).projectAs(arcpy.SpatialReference(32641))
    return [pg1.getPart().X, pg1.getPart().Y], [pg2.getPart().X, pg2.getPart().Y]


def calculate_circle_coordinates(middle_point, rad_angle, radius):

    x1 = middle_point[0] + (math.cos(rad_angle) * radius)
    y1 = middle_point[1] + (math.sin(rad_angle) * radius)
    return [x1, y1]


def calculate_fishnet_parameters(point1, point2, radius=700):

    point1_UTM, point2_UTM = project_point(point1, point2)
    middle_point = calculate_middle(point1_UTM, point2_UTM)
    middle_point_wgs = calculate_middle(point1, point2)
    angle = get_azimuth_polyline(point1_UTM, point2_UTM)
    alf_origXY = 90 - angle + 225
    alf_YAxis = 90 - angle + 135
    rad_alf_origXY = math.radians(alf_origXY)
    rad_alf_YAxis = math.radians(alf_YAxis)
    circle_radius = radius * math.sqrt(2)
    originXY = calculate_circle_coordinates(middle_point, rad_alf_origXY, circle_radius)
    pointYAxis = calculate_circle_coordinates(middle_point, rad_alf_YAxis, circle_radius)
    return originXY, pointYAxis, middle_point_wgs


def create_fishnet(originXY, pointYAxis, row_width=20, row_height=20, column=70, rows=70):

    fishnet = 'in_memory/fishnet'
    with Profiler() as pr:
        print 'fish'
        arcpy.CreateFishnet_management(fishnet, "%s %s"%(originXY[0], originXY[1]), "%s %s"%(pointYAxis[0], pointYAxis[1]), row_width, row_height, column, rows, "", "NO_LABELS", "DEFAULT", "POLYGON")
    arcpy.DefineProjection_management(fishnet, arcpy.SpatialReference(32641))
    return fishnet


def prepare_layers(eo_gdb):


    point_lyr = arcpy.MakeFeatureLayer_management(r'C:\Data\Data_for_IUS\input.gdb\point', 'point')

    line_lyr = arcpy.MakeFeatureLayer_management(r'C:\Data\Data_for_IUS\input.gdb\line', 'line')

    polygon_lyr = arcpy.MakeFeatureLayer_management(r'C:\Data\Data_for_IUS\input.gdb\polygon', 'polygon')

    return [point_lyr, line_lyr, polygon_lyr]


def main_old(point, grid, dataset, out_work):

    with Profiler() as pr:
        print '\t Start preproc'
        arcpy.env.workspace = dataset
        fc_list = arcpy.ListFeatureClasses()
    lines = 'in_memory/lines_L'
    polygons = 'in_memory/polygons_A'
    mem_fc = [lines, polygons]
    for i in fc_list:
        print i

    buf = 'in_memory/buf'
    with Profiler() as pr:
        print '\tCreate buffer'
        point = arcpy.Point(point[0], point[1])
        pg = arcpy.PointGeometry(point)
        arcpy.Buffer_analysis(pg, buf, "700 meters")

    mem_fc_sel = []
    with Profiler() as pr:

        print '\t Select data'
        for fc in fc_list:
            arcpy.Clip_analysis(fc, buf, 'in_memory/'+str(fc)+'_sel')
            mem_fc_sel.append('in_memory/'+str(fc)+'_sel')


    #####################################################################################
    '''
    with Profiler() as pr:
        print '\t Add and calculate Area and Length'
        for fc in fc_list:
            if fc.endswith('L'):
                arcpy.AddField_management(os.path.join(dataset,fc),"Full_length","DOUBLE")
                arcpy.AddField_management(os.path.join(dataset,fc),"Part_length","DOUBLE")
                arcpy.CalculateField_management(os.path.join(dataset,fc),"Full_length","""!shape.length@meters!""","PYTHON_9.3")
            if fc.endswith('A'):
                arcpy.AddField_management(os.path.join(dataset,fc),"Full_area","DOUBLE")
                arcpy.AddField_management(os.path.join(dataset,fc),"Part_area","DOUBLE")
                arcpy.CalculateField_management(os.path.join(dataset,fc),"Full_area","""!shape.area@SQUAREMETERS!""","PYTHON_9.3")
    '''
    #####################################################################################|

    fc_list_mem = []
    grid_mem = 'in_memory/grid'
    fish = 'in_memory/fish'
    '''
    with Profiler() as pr:
        arcpy.Select_analysis(grid, grid_mem)
    '''
    with Profiler() as pr:
        print '\tCreate fishnet'
        #arcpy.CreateFishnet_management(fish, "8652850,03 9619614,3968", "8653550,03 9620314,3968", "47,268", "47,268", "70", "70", "", "NO_LABELS", "DEFAULT", "POLYGON")
        arcpy.CreateFishnet_management(fish, "486207,5255 6493868,383", "486235,8442 6494245,9618", "20", "20", "70", "70", "", "NO_LABELS", "DEFAULT", "POLYGON")


    with Profiler() as pr:
        print '\t Define projection'
        arcpy.DefineProjection_management(fish, arcpy.SpatialReference(32642))

    ##############################################

    res = []
    with Profiler() as p:
        print '\t  Intersetcion full'
        for fc in mem_fc_sel:

            #out_path = os.path.join('in_memory', str(fc)+'_inter')
            #out_path = os.path.join('in_memory', str(fc).split('.')[1]+'_inter')
            #out_path = os.path.join(out_work, str(fc)+'_inter')
            #out_path = 'in_memory/int'+fc
            out_path = fc+'_i'
            res.append(out_path)
            with Profiler() as pr1:
                print '\t\t\t'+fc
                #arcpy.Intersect_analysis([os.path.join(dataset,fc), fish], out_path, 'ALL')
                arcpy.Intersect_analysis([fc, fish], out_path, 'ALL')
            #print fc
    #############
    '''
    with Profiler() as pr:
        arcpy.env.workspace = 'in_memory'
        fc_list = arcpy.ListFeatureClasses()
        for i in fc_list:
            print i
            #arcpy.AddField_management(str(i), 'temp','DOUBLE')
            #arcpy.CalculateField_management(str(i),"temp","""!shape.area@SQUAREMETERS!""","PYTHON_9.3")
    '''
    #############

    ##############################################

    pass


def prepare_eo(eo, mid_point, radius=700):

    eo_list = []
    mid_point_as_point = arcpy.Point(mid_point[0], mid_point[1])
    mid_point_as_pg = arcpy.PointGeometry(mid_point_as_point, arcpy.SpatialReference(4326))

    for layer in eo:
        arcpy.SelectLayerByLocation_management(layer,"WITHIN_A_DISTANCE", mid_point_as_pg, str(radius)+" meters","NEW_SELECTION","NOT_INVERT")
        arcpy.FeatureClassToFeatureClass_conversion(layer, 'in_memory', str(layer)+'_sel')
        #arcpy.FeatureClassToFeatureClass_conversion(layer, 'C:\Data\Data_for_IUS\output.gdb', str(layer)+'_sel')
        fc_name = os.path.join('in_memory', str(layer)+'_sel')
        if str(layer).startswith('line'):
            arcpy.CalculateField_management(fc_name,"Full_length","""!shape.length@meters!""","PYTHON_9.3")
        if str(layer).startswith('polygon'):
            arcpy.CalculateField_management(fc_name,"Full_area","""!shape.area@SQUAREMETERS!""","PYTHON_9.3")

        eo_list.append(fc_name)
    return eo_list


def intersect(eo_list, fishnet):

    for fc in eo_list:
        out_path = os.path.join(r'C:\Data\Data_for_IUS\output.gdb', fc.split('\\')[1])
        arcpy.Intersect_analysis([fc, fishnet], out_path, 'ALL')
        if fc.split('\\')[1].startswith('line'):
            arcpy.CalculateField_management(out_path,"Part_length","""!shape.length@meters!""","PYTHON_9.3")
        if fc.split('\\')[1].startswith('polygon'):
            arcpy.CalculateField_management(out_path,"Part_area","""!shape.area@SQUAREMETERS!""","PYTHON_9.3")


def unit_process(start_point, end_point, eo):

    originXY, pointYAxis, middle_point_wgs = calculate_fishnet_parameters(start_point, end_point)
    fishnet = create_fishnet(originXY, pointYAxis)
    eo_list = prepare_eo(eo, middle_point_wgs)
    intersect(eo_list, fishnet)




    pass


def main(eo, list_coordinates):

    unit_process(list_coordinates[0][0], list_coordinates[0][1], eo)
    #for unit in list_coordinates:
        #unit_process(unit[0], unit[1], eo)

    pass


if __name__ == "__main__":
    #p1_test = [486197.914, 6493865.621]
    #p2_test = [486217.1357, 6493871.146]

    list_coordinates = [[[64.990785, 56.49842],[64.991099,56.498467]],
    [[64.991099, 56.498467],[64.991412, 56.498515]],
    [[64.991412, 56.498515],[64.991725, 56.498562]]]

    eo_stack = prepare_layers('asd')
    main(eo_stack, list_coordinates)



    p1_test = [68.762614, 58.584984]
    p2_test = [68.762945, 58.585034]

    p3_test = [68.763395, 58.585878]
    p4_test = [68.763528, 58.585998]



    #grid = r'C:\Data\temp.gdb\grid_cut_1'
    #dataset = r'C:\Data\merged_10k_v2_1.gdb'
    #dataset = r'C:\Data\repr.gdb'
    #out_work = r'C:\Data\InterRES.gdb'

    #grid = sys.argv[1]
    #dataset = sys.argv[2]
    #out_work = sys.argv[3]
    #with Profiler() as main_pr:
        #main(mid_point, grid, dataset, out_work)
        #print '\tFull proccessing time'

