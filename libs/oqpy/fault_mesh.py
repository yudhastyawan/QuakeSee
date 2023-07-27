from custom_openquake import *

inputfile = sys.argv[1]
outputfile = sys.argv[2]

with open(outputfile, 'rb') as f:
    fault_geoms, fault_props = pickle.load(f)

os.remove(outputfile)

mesh = []
for i, geom in enumerate(fault_geoms):
    line = LineOQ([PointOQ(lon, lat) for lon, lat in zip(*geom)])
    z1, z2, dip, dist = fault_props[i,:]
    m_s = 1
    fault_surface = SimpleFaultSurface.from_fault_data(line, upper_seismogenic_depth=z1, lower_seismogenic_depth=z2, 
                                                       dip=dip, mesh_spacing=m_s)
    mesh.append([fault_surface.mesh.lons, fault_surface.mesh.lats, fault_surface.mesh.depths])

with open(outputfile, 'wb') as f:
    pickle.dump(mesh, f)