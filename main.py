# -*- coding:utf-8 -*-
try:
    from typing import List, Tuple, Dict, Any, Optional
except ImportError:
    pass

import math

import scriptcontext as sc
import Rhino  # type: ignore
import Rhino.Geometry as geo  # type: ignore
import ghpythonlib.components as ghcomp

import time

BIGNUM = 1000000
OP_TOL = 0.0001


def is_pt_inside(region, pt, plane=geo.Plane.WorldXY, tol=OP_TOL):
    # type: (geo.Curve, geo.Point3d, geo.Plane, float) -> int
    # clipper 보다 10배 빠름
    containment = region.Contains(pt, plane, tol)

    return containment == geo.PointContainment.Inside


class Road:

    def __init__(self, centerline):
        # type: (geo.Curve) -> None
        self.center_crv = centerline
        self.mid_pt = centerline.PointAtNormalizedLength(0.5)
        self.st_pt = centerline.PointAtStart
        self.en_pt = centerline.PointAtEnd

        self.length = round(centerline.GetLength(), 2)

        self.st_pt_on_topo = None  # type: geo.Point3d
        self.st_pt_on_topo = None  # type: geo.Point3d
        self.height = None  # type: float
        self.road_region = None  # type: geo.Curve

    def set_height(self, topo):
        # type: (geo.Mesh) -> bool

        def get_projected_pt_on_mesh(pt, mesh):
            # type: (geo.Point3d, geo.Mesh) -> geo.Point3d | None
            # Z축 방향 레이 생성
            ray = geo.Ray3d(pt, geo.Vector3d(0, 0, -1))  # Z축 아래 방향
            t = geo.Intersect.Intersection.MeshRay(mesh, ray)

            if t >= 0:
                # 레이의 t 값으로 교차점 계산
                return ray.PointAt(t)

            ray = geo.Ray3d(pt, geo.Vector3d(0, 0, 1))  # Z축 윗 방향
            t = geo.Intersect.Intersection.MeshRay(mesh, ray)

            if t >= 0:
                # 레이의 t 값으로 교차점 계산
                return ray.PointAt(t)

            return None  # 교차가 없을 경우 None 반환

        self.st_pt_on_topo = get_projected_pt_on_mesh(self.st_pt, topo)
        self.en_pt_on_topo = get_projected_pt_on_mesh(self.en_pt, topo)

        # 도로의 끝점이 토포그래피를 벗어나는등의 이유로 높이 설정이 실패하는 경우
        if not (self.st_pt_on_topo and self.en_pt_on_topo):
            return False

        self.height = abs(self.st_pt_on_topo.Z - self.en_pt_on_topo.Z)
        return True

    @property
    def slope_percentage(self):
        # type: () -> float
        if self.height is None:
            raise Exception("NO HEIGHT")

        return self.height / self.length

    def is_steep(self, steep_percentage):
        # type: (float) -> bool

        return self.slope_percentage > steep_percentage


stime = time.time()

# input :  topo(geo.Mesh), road_centerlines(List[geo.Curve]), road_regions(List[geo.Curve]), steep_percentage(float)

roads = [Road(centerline) for centerline in road_centerlines]

steep_roads = []
for road in roads:

    # road의 height 설정
    is_height_available = road.set_height(topo)
    if not is_height_available:
        continue

    # 가파른 도로 처리
    if not road.is_steep(steep_percentage):
        continue

    # road와 매칭될 region 설정
    matched_region = None
    for region in road_regions:
        if is_pt_inside(region, road.mid_pt):
            matched_region = region
            road.road_region = matched_region
            road_regions = [
                region for region in road_regions if region is not matched_region
            ]
            break

    steep_roads.append(road.road_region)

output = (
    "Total Roads = "
    + str(len(roads))
    + "\n"
    + "Steep Roads = "
    + str(len(steep_roads))
    + "\n"
    + str(round(len(steep_roads) / len(roads) * 100, 2))
    + "% of road is steep"
    + "\n"
)

etime = time.time()

print("TIME", etime - stime)
