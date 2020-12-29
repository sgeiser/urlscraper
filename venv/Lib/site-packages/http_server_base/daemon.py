"""
Generic linux daemon base class for python 3.x.
"""

import atexit
import os
import signal
import sys
import time

from subprocess import Popen, PIPE
from typing import *

def execute(command: str, *, raise_on_failure: Union[bool, str] = False, use_pipe: bool = True) -> Tuple[int, bytes, bytes]:
    print('Executing command: {command}'.format(command=command))
    process = Popen \
    (
        args = command,
        stdout = PIPE if (use_pipe) else None,
        stderr = PIPE if (use_pipe) else None,
        shell = True,
    )
    _stdout, _stderr = process.communicate() # type: bytes, bytes
    if (raise_on_failure):
        assert process.returncode == 0, \
            (raise_on_failure if (isinstance(raise_on_failure, str)) else f"Command {command} did not end successfully.") + "\n" \
            f"Std Out: {_stdout.decode() if (_stdout) else ''}\n" \
            f"Std Err: {_stderr.decode() if (_stderr) else ''}\n" \
    
    return process.returncode, _stdout, _stderr


class Daemon:
    """
    A generic daemon class.
    Usage: subclass the daemon class and override the run() method.
    """
    
    pidfile: str = None
    exec_name: str = None
    
    def __init__(self, pidfile: str = None, exec_name: str = None):
        if (pidfile is not None):
            self.pidfile = pidfile
        if (exec_name is not None):
            self.exec_name = exec_name
        
        if (self.pidfile is None):
            raise ValueError("pidfile is not set")
        if (self.exec_name is None):
            self.exec_name = sys.argv[0]
    
    def daemonize(self):
        """
        Deamonize class. UNIX double fork mechanism.
        """
        
        self.fork(1)
        
        # decouple from parent environment
        os.chdir('/')
        os.setsid()
        os.umask(0)
        
        # do second fork
        self.fork(2)
        
        # redirect standard file descriptors
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())
        
        # write pidfile
        atexit.register(self.delpid)
        
        pid = str(os.getpid())
        with open(self.pidfile,'w+') as f:
            f.write(pid + '\n')
    
    def fork(self, id: int = 1):
        try:
            pid = os.fork()
            if (pid > 0):
                # exit first parent
                sys.exit(0)
        except OSError as err:
            sys.stderr.write(f"Fork #{id} failed: {err}\n")
            sys.exit(1)

    def delpid(self):
        os.remove(self.pidfile)
    @property
    def pid(self) -> Optional[int]:
        try:
            with open(self.pidfile,'r') as pf:
                return int(pf.read().strip())
        except IOError:
            return None
    
    def start(self):
        """
        Start the daemon.
        """
        
        # Check for a pidfile to see if the daemon already runs
        if (self.pid):
            message = "pidfile {0} already exist. " + \
                    "Daemon already running?\n"
            sys.stderr.write(message.format(self.pidfile))
            sys.exit(0)
        
        # Start the daemon
        self.daemonize()
        self.run()
    
    def stop(self, force: bool = False):
        """
        Stop the daemon.
        """
        
        # Get the pid from the pidfile
        try:
            with open(self.pidfile,'r') as pf:
                pid = int(pf.read().strip())
        except IOError:
            pid = None
        
        if (not pid and not force):
            print(f"pidfile {self.pidfile} does not exist. Daemon not running?", file=sys.stderr)
            return
        
        elif (not pid and force):
            print(f"Stopping application ('{self.exec_name}') forcibly...?", file=sys.stderr)
            try:
                _, stdout, stderr = execute(f'ps aux | grep -v grep | grep {self.exec_name}')
                assert stdout
                lines = stdout.decode().split('\n')
                _self = os.getpid()
                for p in lines:
                    try:
                        _pid = int(p.split()[1])
                    except (IndexError, ValueError):
                        pass
                    else:
                        if (_pid != _self):
                            self.kill(_pid)
            except AssertionError:
                print(f"Cannot stop application: '{self.pidfile}'", file=sys.stderr)
                sys.exit(1)
            else:
                return
        
        elif (pid):
            self.kill(pid)
            return
    
    def kill(self, pid):
        # Try killing the daemon process
        try:
            while 1:
                os.kill(pid, signal.SIGTERM)
                time.sleep(0.1)
        except OSError as err:
            e = str(err.args)
            if (e.find("No such process") > 0):
                if (os.path.exists(self.pidfile)):
                    os.remove(self.pidfile)
            else:
                print (str(err.args))
                sys.exit(1)
    
    def restart(self):
        """
        Restart the daemon.
        """
        
        self.stop()
        self.start()
    
    def run(self):
        """
        You should override this method when you subclass Daemon.
        
        It will be called after the process has been daemonized by
        start() or restart().
        """
        
        raise NotImplementedError()

__all__ = \
[
    'Daemon',
]
