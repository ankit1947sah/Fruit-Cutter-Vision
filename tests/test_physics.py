import unittest
from physics import PhysicsState

class TestPhysicsState(unittest.TestCase):
    
    def test_initial_state(self):
        state = PhysicsState(x=10.0, y=20.0, vx=5.0, vy=-5.0, ay=100.0)
        self.assertEqual(state.x, 10.0)
        self.assertEqual(state.y, 20.0)
        self.assertEqual(state.vx, 5.0)
        self.assertEqual(state.vy, -5.0)
        self.assertEqual(state.ay, 100.0)
        self.assertEqual(state.angle, 0.0)
        
    def test_update_integration(self):
        # ax=0, ay=100
        state = PhysicsState(x=0.0, y=0.0, vx=10.0, vy=5.0, ax=0.0, ay=100.0, angular_velocity=45.0)
        dt = 0.1 # 100ms
        
        state.update(dt)
        # vy = vy_init + ay*dt = 5.0 + 100.0*0.1 = 15.0
        # vx = vx_init + ax*dt = 10.0
        # x = x_init + vx*dt = 0.0 + 10.0*0.1 = 1.0
        # y = y_init + vy*dt = 0.0 + 15.0*0.1 = 1.5
        # angle = angle_init + av*dt = 0.0 + 45.0*0.1 = 4.5
        
        self.assertAlmostEqual(state.vx, 10.0)
        self.assertAlmostEqual(state.vy, 15.0)
        self.assertAlmostEqual(state.x, 1.0)
        self.assertAlmostEqual(state.y, 1.5)
        self.assertAlmostEqual(state.angle, 4.5)
        
    def test_apply_force(self):
        state = PhysicsState(vx=5.0, vy=5.0)
        state.apply_force(-10.0, 15.0)
        self.assertEqual(state.vx, -5.0)
        self.assertEqual(state.vy, 20.0)
        
    def test_angle_wrap_around(self):
        state = PhysicsState(angle=350.0, angular_velocity=20.0)
        state.update(1.0) # angle = 370.0 -> wrap to 10.0
        self.assertEqual(state.angle, 10.0)
        
        state = PhysicsState(angle=10.0, angular_velocity=-20.0)
        state.update(1.0) # angle = -10.0 -> wrap to 350.0
        self.assertEqual(state.angle, 350.0)
        
if __name__ == '__main__':
    unittest.main()
