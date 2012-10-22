import contextlib
import logging
import os

from teuthology import misc as teuthology

log = logging.getLogger(__name__)

def task(ctx, config):
    """
    Execute commands on a given role

        tasks:
        - ceph:
        - kclient: [client.a]
        - exec:
            client.a:
              - echo 'module libceph +p' > /sys/kernel/debug/dynamic_debug/control
              - echo 'module ceph +p' > /sys/kernel/debug/dynamic_debug/control
        - interactive:

    """
    log.info('Executing custom commands...')
    assert isinstance(config, dict), "task exec got invalid config"

    if 'all' in config and len(config) == 1:
        a = config['all']
        roles = teuthology.all_roles(ctx.cluster)
        config = dict((id_, a) for id_ in roles)

    for role, ls in config.iteritems():
        (remote,) = ctx.cluster.only(role).remotes.iterkeys()
        log.info('Running commands on role %s host %s', role, remote.name)
        for c in ls:
            remote.run(
                args=[
                    'sudo',
                    'bash',
                    '-c',
                    c],
                )

