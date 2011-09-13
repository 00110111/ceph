from . import run

class Remote(object):
    """
    A connection to a remote host.

    This is a higher-level wrapper around Paramiko's `SSHClient`.
    """

    # for unit tests to hook into
    _runner = staticmethod(run.run)

    def __init__(self, name, ssh, shortname=None):
        self.name = name
        self._shortname = shortname
        self.ssh = ssh

    @property
    def shortname(self):
        name = self._shortname
        if name is None:
            name = self.name
        return name

    def __str__(self):
        return self.shortname

    def __repr__(self):
        return '{classname}(name={name!r})'.format(
            classname=self.__class__.__name__,
            name=self.name,
            )

    def run(self, **kwargs):
        """
        This calls `orchestra.run.run` with our SSH client.

        TODO refactor to move run.run here?
        """
        r = self._runner(client=self.ssh, **kwargs)
        r.remote = self
        return r
