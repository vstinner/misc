# Author: Victor Stinner
# Creation date: 2007-04-03
# License: GNU GPL v2

from thread import allocate_lock, start_new_thread
from sys import stderr

class StoppableThread:
    """
    Stoppable thread class:
     - start(): start the thread
     - stop(): stop the thread

    User defined methods:
     - run(): one step of the thread
     - deinit(): method called on thread's end
     - errorHandler(): process thread exception

    The thread is only stoppable is run() maximum duration is not bigger
    than one second. If run() runs longer, stop() call will also be longer.
    """
    def __init__(self):
        self._run_lock = allocate_lock()
        self._stop_lock = allocate_lock()

    def start(self):
        start_new_thread(self._threadFunc, tuple())

    def _threadFunc(self):
        self._run_lock.acquire()
        try:
            try:
                while self._stop_lock.acquire(0):
                    self._stop_lock.release()
                    self.run()
            except Exception, err:
                self.errorHandler(err)
        finally:
            self._run_lock.release()

    def stop(self):
        self._stop_lock.acquire()
        self._run_lock.acquire()
        self._run_lock.release()
        self._stop_lock.release()
        self.deinit()

    #--- Abstract methods -------------------

    def run(self):
        """
        Main code of the thread: have to be faster than one second
        to be able to stop the thread.
        """
        raise NotImplementedError()

    def errorHandler(self, err):
        print >>stderr, "THREAD ERROR (%s): %s" % (err.__class__.__name__, err)

    def deinit(self):
        pass

