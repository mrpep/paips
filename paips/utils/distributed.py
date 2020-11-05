import ray

def method_wrapper(instance,name,args=[],kwargs={}):
     return getattr(instance,name)(*args,**kwargs)

class ActorWrapper:
    def __init__(self,*args,**kwargs):
        actor = kwargs.pop('actor')

        def get(self_,name):
            print(name)
            return getattr(self_,name)

        actor.get = get
        self.actor = ray.remote(actor)
        self.actor = self.actor.remote(*args,**kwargs)
        
    def return_callable(self,actor=None):
        def callme(*args,**kwargs):
            return ray.get(actor.remote(*args,**kwargs))
        return callme
        
    def __getattr__(self,name):
        if hasattr(self.actor,name):
            print('!!! {}'.format(name))
            method = getattr(self.actor,name)
            wrapper_fn = self.return_callable(method)
        else:
            print(name)
            wrapper_fn = ray.get(self.actor.get.remote(name))

        return wrapper_fn