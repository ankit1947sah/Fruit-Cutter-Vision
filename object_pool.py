from logger import log

class ObjectPool:
    """A generic, fast object pooling implementation to reduce garbage collection spikes."""
    
    def __init__(self, factory_function, initial_size=50, name="GenericPool"):
        self.factory_function = factory_function
        self.name = name
        self.pool = []
        
        # Pre-populate pool
        for _ in range(initial_size):
            self.pool.append(self.factory_function())
            
        log.info("Initialized ObjectPool '%s' with %d pre-allocated objects.", name, initial_size)
        
    def acquire(self, *args, **kwargs):
        """Retrieves an object from the pool. Creates a new one if the pool is exhausted.
        
        It is expected that the acquired object has a `.reset(*args, **kwargs)` method 
        to reinitialize its state.
        """
        if self.pool:
            obj = self.pool.pop()
        else:
            # Log warnings occasionally in dev mode if pool is constantly resizing
            # but create new objects to avoid crashing.
            obj = self.factory_function()
            
        # Re-initialize the object if a reset method exists
        if hasattr(obj, "reset"):
            obj.reset(*args, **kwargs)
            
        return obj
        
    def release(self, obj):
        """Returns a used object back to the pool."""
        self.pool.append(obj)
        
    def get_free_count(self):
        """Returns the number of available objects in the pool."""
        return len(self.pool)
