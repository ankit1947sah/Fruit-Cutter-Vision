import os
import sys
import time
import random

# Force headless execution for benchmark compatibility (no window display, no hardware audio)
os.environ["SDL_VIDEODRIVER"] = "dummy"
os.environ["SDL_AUDIODRIVER"] = "dummy"

import pygame
import config
from logger import log

# Initialize procedural fruits cached shapes and audio synthesizer before loading engine
import fruit
import audio

# Mocking psutil imports
try:
    import psutil
    _process = psutil.Process(os.getpid())
except ImportError:
    _process = None

from game_engine import GameEngine
from state_manager import GameState

def run_performance_benchmark(num_frames=600):
    """Executes a headless simulation of gameplay and logs performance telemetry."""
    print("=========================================")
    print(f"Starting Headless Performance Benchmark ({num_frames} frames)...")
    print("=========================================")
    
    # Override developer mode and fullscreen for benchmark consistency
    config.DEVELOPER_MODE = False
    config.FULLSCREEN = False
    
    # Initialize Engine
    engine = GameEngine()
    
    # Warm up systems
    fruit.initialize_procedural_fruits()
    audio.synth.init_mixer()
    audio.synth.generate_all_sounds()
    
    # Force Playing state directly
    engine.state_mgr.transition_to(GameState.PLAYING)
    engine.score_sys.reset()
    
    # Lists for metric gathering
    fps_metrics = []
    frame_time_metrics = []
    cpu_metrics = []
    mem_metrics = []
    particle_counts = []
    
    frame_count = 0
    dt = 1.0 / 60.0 # Fixed step simulation
    
    # Mocking slice triggers
    # We simulate pointer sweeps across the screen to slice fruits
    log.info("Headless benchmark game loop active. Simulating inputs...")
    
    start_bench_time = time.perf_counter()
    
    while frame_count < num_frames:
        frame_start = time.perf_counter()
        
        # Simulate index finger pointer moving in a sinusoidal sweeping blade stroke
        sweep_x = int(config.WIDTH / 2 + 300 * np.sin(frame_count * 0.1)) if 'np' in globals() else int(config.WIDTH / 2 + 300 * random.uniform(-1, 1))
        sweep_y = int(config.HEIGHT / 2 + 200 * random.uniform(-0.5, 0.5))
        
        engine.prev_pointer_pos = engine.curr_pointer_pos
        engine.curr_pointer_pos = (sweep_x, sweep_y)
        engine.blade_trail.add_point(sweep_x, sweep_y)
        
        # Randomly trigger a mouse pinch trigger
        engine.is_pinching = (frame_count % 15 == 0)
        engine.hand_detected = True
        
        # Step game engine mechanics
        engine._update_playing(dt)
        engine.blade_trail.update(dt)
        
        # Periodically spawn fruits manually to stress test particle/collision systems
        if frame_count % 45 == 0:
            engine._spawn_wave()
            
        # Draw frame onto dummy canvas
        engine.canvas.fill(config.COLOR_BACKGROUND)
        engine._draw_playing()
        
        # Tick clock (simulated delay limit)
        engine.clock.tick(config.FPS)
        
        # Record metrics
        frame_end = time.perf_counter()
        f_time = (frame_end - frame_start) * 1000.0 # ms
        frame_time_metrics.append(f_time)
        
        # Calculate instant FPS
        instant_fps = 1000.0 / f_time if f_time > 0 else 60.0
        fps_metrics.append(min(instant_fps, 60.0))
        
        # Capture CPU & Memory
        if _process and frame_count % 30 == 0:
            try:
                cpu_metrics.append(psutil.cpu_percent())
                mem_mb = _process.memory_info().rss / (1024 * 1024)
                mem_metrics.append(mem_mb)
            except Exception:
                pass
                
        particle_counts.append(len(engine.particle_mgr.active_particles))
        
        frame_count += 1
        
    bench_duration = time.perf_counter() - start_bench_time
    
    # 3. Analyze Metrics
    avg_fps = sum(fps_metrics) / len(fps_metrics)
    avg_f_time = sum(frame_time_metrics) / len(frame_time_metrics)
    max_f_time = max(frame_time_metrics)
    
    avg_cpu = sum(cpu_metrics) / len(cpu_metrics) if cpu_metrics else 0.0
    avg_mem = sum(mem_metrics) / len(mem_metrics) if mem_metrics else 0.0
    max_mem = max(mem_metrics) if mem_metrics else 0.0
    
    avg_particles = sum(particle_counts) / len(particle_counts)
    max_particles = max(particle_counts)
    
    # Ensure logs folder exists
    os.makedirs(config.SAVE_DIR, exist_ok=True)
    report_path = os.path.join(config.SAVE_DIR, "benchmark_report.txt")
    
    # 4. Generate Report Document
    report = f"""=====================================================
FRUIT CUTTER VISION - PERFORMANCE BENCHMARK REPORT
=====================================================
Execution Context:
  Date/Time: {time.strftime('%Y-%m-%d %H:%M:%S')}
  Frames Executed: {num_frames}
  Target FPS: {config.FPS}
  Benchmark Duration: {bench_duration:.2f} seconds
  Platform: {sys.platform}

Metrics Summary:
  Average FPS: {avg_fps:.1f}
  Average Frame Time: {avg_f_time:.2f} ms (Target < 16.6ms)
  Maximum Frame Spike: {max_f_time:.2f} ms
  
Memory & CPU Utilization:
  Average CPU Usage: {avg_cpu:.1f}%
  Average Memory Footprint: {avg_mem:.1f} MB (Target < 300MB)
  Peak Memory Footprint: {max_mem:.1f} MB

Object Activity:
  Average Active Particles: {avg_particles:.1f}
  Peak Active Particles: {max_particles}
  Remaining Fruit Pool Free Size: {engine.fruit_pool.get_free_count()}
  Remaining Particle Pool Free Size: {engine.particle_pool.get_free_count()}

System Health Assessment:
  GC Overhead Spikes: {'NO' if max_f_time < 30.0 else 'YES (Frame spike detected)'}
  Stable 60 FPS Achieved: {'YES' if avg_fps >= 58.0 else 'NO (Below target threshold)'}
  Memory Leak Check: {'PASSED' if max_mem - (mem_metrics[0] if mem_metrics else 0) < 5.0 else 'FAILED (Growth detected)'}
====================================================="""
    
    print(report)
    
    with open(report_path, 'w') as f:
        f.write(report)
        
    print(f"\nSaved benchmark performance report to {report_path}")
    
    # Shutdown
    engine.camera.stop()
    engine.tracker.stop()
    pygame.quit()
    
    return avg_fps, avg_f_time, avg_mem

if __name__ == "__main__":
    # Import numpy here for benchmark sweep mathematics
    import numpy as np
    run_performance_benchmark()
