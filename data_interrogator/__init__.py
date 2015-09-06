from views import interrogation_room, interrogate

from data_interrogator.urls import urlpatterns
urls = (urlpatterns, 'data_interrogator', 'data_interrogator')

__version_info__ = {
    'major': 0,
    'minor': 0,
    'micro': 1,
    'releaselevel': 'beta',
    'serial': 1
}


def get_version(release_level=True):
    """
    Return the formatted version information
    """
    vers = ["%(major)i.%(minor)i.%(micro)i" % __version_info__]
    if release_level and __version_info__['releaselevel'] != 'final':
        vers.append('%(releaselevel)s%(serial)i' % __version_info__)
    return ''.join(vers)


__version__ = get_version()