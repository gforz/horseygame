
"""Pixel-space helpers backed by the PyBox2D engine."""

from typing import NamedTuple

from Box2D import b2World

PIXELS_PER_METER = 100.0


class Vector(NamedTuple):
    x: float
    y: float


def _to_meters(point) -> tuple[float, float]:
    return (
        point[0] / PIXELS_PER_METER,
        point[1] / PIXELS_PER_METER,
    )


def _to_pixels(point) -> Vector:
    return Vector(
        point[0] * PIXELS_PER_METER,
        point[1] * PIXELS_PER_METER,
    )


def torque_to_box2d(torque_in_pixel_units: float) -> float:
    return torque_in_pixel_units / (
        PIXELS_PER_METER * PIXELS_PER_METER
    )


class PhysicsBody:
    def __init__(self, body) -> None:
        self.native = body

    @property
    def position(self) -> Vector:
        return _to_pixels(self.native.position)

    @position.setter
    def position(self, value) -> None:
        self.native.position = _to_meters(value)

    @property
    def velocity(self) -> Vector:
        return _to_pixels(self.native.linearVelocity)

    @velocity.setter
    def velocity(self, value) -> None:
        self.native.linearVelocity = _to_meters(value)

    @property
    def angle(self) -> float:
        return self.native.angle

    @angle.setter
    def angle(self, value: float) -> None:
        self.native.angle = value

    @property
    def angular_velocity(self) -> float:
        return self.native.angularVelocity

    @angular_velocity.setter
    def angular_velocity(self, value: float) -> None:
        self.native.angularVelocity = value

    def local_to_world(self, point) -> Vector:
        return _to_pixels(
            self.native.GetWorldPoint(_to_meters(point))
        )


class PhysicsSpace:
    def __init__(self, gravity_pixels: float) -> None:
        self.world = b2World(
            gravity=(0, gravity_pixels / PIXELS_PER_METER),
            doSleep=True,
        )

    def step(self, dt: float) -> None:
        self.world.Step(dt, 8, 3)
        self.world.ClearForces()

    def add_edge(
        self,
        start,
        end,
        friction: float,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ) -> None:
        body = self.world.CreateStaticBody()

        fixture = body.CreateEdgeFixture(
            vertices=(
                _to_meters(start),
                _to_meters(end),
            ),
            friction=friction,
            restitution=0,
        )

        self._set_collision_filter(
            fixture,
            collision_category,
            collision_mask,
        )

    @staticmethod
    def _set_collision_group(fixture, group_index: int) -> None:
        if group_index:
            filter_data = fixture.filterData
            filter_data.groupIndex = -abs(group_index)
            fixture.filterData = filter_data

    @staticmethod
    def _set_collision_filter(
        fixture,
        category_bits: int,
        mask_bits: int,
    ) -> None:
        filter_data = fixture.filterData
        filter_data.categoryBits = category_bits
        filter_data.maskBits = mask_bits
        fixture.filterData = filter_data

    def add_hoof_fixture(
        self,
        body: PhysicsBody,
        vertices,
        friction: float,
        group_index: int,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ) -> None:
        fixture = body.native.CreatePolygonFixture(
            vertices=[
                _to_meters(vertex)
                for vertex in vertices
            ],
            density=0,
            friction=friction,
            restitution=0,
        )

        self._set_collision_filter(
            fixture,
            collision_category,
            collision_mask,
        )

        self._set_collision_group(fixture, group_index)

    def create_box_body(
        self,
        mass: float,
        position,
        size,
        angle: float,
        friction: float,
        group_index: int,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ) -> PhysicsBody:

        width, height = _to_meters(size)

        body = self.world.CreateDynamicBody(
            position=_to_meters(position),
            angle=angle,
            linearDamping=0.005,
            angularDamping=0.005,
        )

        fixture = body.CreatePolygonFixture(
            box=(width / 2, height / 2),
            density=mass / (width * height),
            friction=friction,
            restitution=0,
        )

        self._set_collision_filter(
            fixture,
            collision_category,
            collision_mask,
        )

        self._set_collision_group(fixture, group_index)

        return PhysicsBody(body)

    def create_polygon_body(
        self,
        mass: float,
        position,
        vertices,
        angle: float,
        friction: float,
        group_index: int,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ) -> PhysicsBody:

        area = abs(sum(
            vertices[index][0] * vertices[
                (index + 1) % len(vertices)
            ][1]
            - vertices[
                (index + 1) % len(vertices)
            ][0] * vertices[index][1]
            for index in range(len(vertices))
        )) / 2

        if area <= 0:
            raise ValueError(
                "Polygon body vertices must enclose a non-zero area"
            )

        body = self.world.CreateDynamicBody(
            position=_to_meters(position),
            angle=angle,
            linearDamping=0.005,
            angularDamping=0.005,
        )

        fixture = body.CreatePolygonFixture(
            vertices=[
                _to_meters(vertex)
                for vertex in vertices
            ],
            density=mass * PIXELS_PER_METER ** 2 / area,
            friction=friction,
            restitution=0,
        )

        self._set_collision_filter(
            fixture,
            collision_category,
            collision_mask,
        )

        self._set_collision_group(fixture, group_index)

        return PhysicsBody(body)

    def create_compound_polygon_body(
        self,
        mass: float,
        position,
        polygons,
        angle: float,
        friction: float,
        group_index: int,
        collision_category: int = 0x0001,
        collision_mask: int = 0xFFFF,
    ) -> PhysicsBody:

        polygon_areas = [
            abs(sum(
                polygon[index][0] * polygon[
                    (index + 1) % len(polygon)
                ][1]
                - polygon[
                    (index + 1) % len(polygon)
                ][0] * polygon[index][1]
                for index in range(len(polygon))
            )) / 2
            for polygon in polygons
        ]

        total_area = sum(polygon_areas)

        if total_area <= 0:
            raise ValueError(
                "Compound polygon body must enclose a non-zero area"
            )

        body = self.world.CreateDynamicBody(
            position=_to_meters(position),
            angle=angle,
            linearDamping=0.005,
            angularDamping=0.005,
        )

        for polygon in polygons:
            fixture = body.CreatePolygonFixture(
                vertices=[
                    _to_meters(vertex)
                    for vertex in polygon
                ],
                density=1,
                friction=friction,
                restitution=0,
            )

            self._set_collision_filter(
                fixture,
                collision_category,
                collision_mask,
            )

            self._set_collision_group(fixture, group_index)

        density = mass / body.mass

        for fixture in body.fixtures:
            fixture.density = density

        body.ResetMassData()

        return PhysicsBody(body)

    def create_revolute_joint(
        self,
        body_a: PhysicsBody,
        body_b: PhysicsBody,
        anchor,
        lower_angle: float,
        upper_angle: float,
        max_motor_torque: float,
    ):
        return self.world.CreateRevoluteJoint(
            bodyA=body_a.native,
            bodyB=body_b.native,
            anchor=_to_meters(anchor),
            enableLimit=True,
            lowerAngle=lower_angle,
            upperAngle=upper_angle,
            enableMotor=True,
            motorSpeed=0,
            maxMotorTorque=max_motor_torque,
            collideConnected=False,
        )

    def remove(self, *bodies: PhysicsBody) -> None:
        for body in bodies:
            self.world.DestroyBody(body.native)
