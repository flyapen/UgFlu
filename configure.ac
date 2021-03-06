-*- mode: m4 -*-

m4_define([flu_major_version], [0])
m4_define([flu_minor_version], [5])
m4_define([flu_micro_version], [4])
m4_define([flu_extra_version], [0])
m4_define([flu_version], [flu_major_version.flu_minor_version.flu_micro_version])

AC_INIT(flumotion, [flu_version])
AM_INIT_AUTOMAKE([-Wno-portability])

AS_VERSION(flumotion, FLUMOTION,
           flu_major_version,
           flu_minor_version,
           flu_micro_version,
           flu_extra_version)
AC_SUBST(RELEASE, $FLUMOTION_RELEASE)

AC_SUBST_FILE(AUTHORS)
AUTHORS=$srcdir/AUTHORS

dnl keep in sync with flumotion/common/boot.py and
dnl                   flumotion.spec.in
AC_SUBST(PYGTK_010_REQ, 2.8.4)
AC_SUBST(PYGST_010_REQ, 0.10.0)
AC_SUBST(GST_010_REQ, 0.10.0.1)

GST_010_SUPPORTED=true

dnl Add parameters for aclocal
AC_SUBST(ACLOCAL_AMFLAGS, "-I m4 -I common")

dnl set up gettext
dnl the version check needs to stay here because autopoint greps for it
AM_GNU_GETTEXT_VERSION([0.11.5])
AM_GNU_GETTEXT([external])

GETTEXT_PACKAGE=$PACKAGE
AC_SUBST(GETTEXT_PACKAGE)

AC_PROG_INTLTOOL([0.34.2])

AS_AC_EXPAND(LIBDIR, $libdir)
AC_MSG_NOTICE(Storing library files in $LIBDIR)

AS_AC_EXPAND(DATADIR, $datadir)
AC_MSG_NOTICE(Storing data files in $DATADIR)

AS_AC_EXPAND(SYSCONFDIR, $sysconfdir)
AC_MSG_NOTICE(Storing configuration files in $SYSCONFDIR)

AS_AC_EXPAND(LOCALSTATEDIR, $localstatedir)
AC_MSG_NOTICE(Using localstatedir $LOCALSTATEDIR)

AS_AC_EXPAND(BINDIR, $bindir)
AC_MSG_NOTICE(Using bindir $BINDIR)

AS_AC_EXPAND(SBINDIR, $sbindir)
AC_MSG_NOTICE(Using sbindir $SBINDIR)

AC_DISABLE_STATIC
AS_LIBTOOL_TAGS([])
AC_PROG_LIBTOOL

dnl check for python
AS_PATH_PYTHON(2.3)

AM_CHECK_PYTHON_HEADERS(HAVE_PYTHON_H=yes, [
  AC_MSG_ERROR([You need to install the Python development packages.])
])

as_save_PYTHONPATH=$PYTHONPATH
PYTHONPATH=$srcdir:$PYTHONPATH
export PYTHONPATH

dnl check for pygtk
AS_PYTHON_IMPORT(pygtk,,AC_MSG_ERROR([pygtk not found or too old]),,
    [from flumotion.common import boot; boot.init_gobject()])

dnl check for gstreamer and gst-python
AS_PYTHON_IMPORT(pygst,,AC_MSG_ERROR([gst-python not found or too old]),,
    [from flumotion.common import boot; boot.init_gobject(); boot.init_gst()])

dnl check for kiwi
AS_PYTHON_IMPORT(kiwi,,AC_MSG_ERROR([kiwi not found or too old]),,
    [from flumotion.common import boot; boot.init_kiwi()])

PYTHONPATH=$as_save_PYTHONPATH
export PYTHONPATH

PKG_CHECK_MODULES(GTK, gtk+-2.0, HAVE_GTK=yes, HAVE_GTK=no)

# decide on tray icon
BUILD_TRAYICON=yes
if test "x$HAVE_PYTHON_H" = "xno"
then
  AC_MSG_NOTICE([Python headers missing, not building tray icon])
  BUILD_TRAYICON=no
fi
if test "x$HAVE_GTK" = "xno"
then
  AC_MSG_NOTICE([GTK+ 2 development files missing, not building tray icon])
  BUILD_TRAYICON=no
fi

if test "x$BUILD_TRAYICON" = "xyes"
then
  AC_MSG_NOTICE([Building tray icon])

  PKG_CHECK_MODULES(PYGTK, pygtk-2.0)
  dnl check stuff we can generate the tray icon with
  AC_MSG_CHECKING(for pygtk codegen)
  PYGTK_CODEGEN="$PYTHON `$PKG_CONFIG --variable=codegendir pygtk-2.0`/codegen.py"
  dnl PYGTK_CODEGEN="$PYTHON \$(top_srcdir)/codegen/codegen.py"
  AC_SUBST(PYGTK_CODEGEN)
  AC_MSG_RESULT($PYGTK_CODEGEN)

  AC_MSG_CHECKING(for pygtk defsdir)
  PYGTK_DEFSDIR=`$PKG_CONFIG --variable=defsdir pygtk-2.0`
  AC_SUBST(PYGTK_DEFSDIR)
  AC_MSG_RESULT($PYGTK_DEFSDIR)
fi

AM_CONDITIONAL(BUILD_TRAYICON, test "x$BUILD_TRAYICON" = "xyes")


dnl XVFB can be used for documentation building and testing because
dnl some things need to import gtk
AC_CHECK_PROG(XVFB, Xvfb, yes, no)

dnl check for documentation
AC_ARG_ENABLE(docs,
              [AC_HELP_STRING([--enable-docs],
                              [create flumotion documentation [default=yes]])],,
              [enable_docs=yes])

if test "x$enable_docs" = "xyes"; then
    AC_CHECK_PROG(EPYDOC, epydoc, yes, no)
    if test "x$EPYDOC" = "xno"; then
      enable_docs=no
    fi
    if test "x$XVFB" = "xno"; then
      enable_docs=no
    fi
else
    EPYDOC=no
fi

AM_CONDITIONAL(HAVE_EPYDOC, test "x$EPYDOC" = "xyes")
AM_CONDITIONAL(BUILD_DOCS, test "x$enable_docs" = "xyes")

dnl check for pychecker
AC_CHECK_PROG(PYCHECKER, pychecker, yes, no)
AM_CONDITIONAL(HAVE_PYCHECKER, test "x$PYCHECKER" = "xyes")

dnl check for Twisted
AS_PYTHON_IMPORT(twisted,
  [
  AC_MSG_CHECKING(for Twisted >= 2.0.1)
  prog="
import sys
import twisted.copyright
minver = '2.0.1'
if twisted.copyright.version < minver:
    sys.exit(1)
sys.exit(0)
"
  if $PYTHON -c "$prog" 1>&AC_FD_CC 2>&AC_FD_CC
  then
    AC_MSG_RESULT(found)
  else
    AC_MSG_RESULT(too old)
    AC_MSG_ERROR([You need at least version 2.0.1 of Twisted])
  fi
  ]
  ,
  AC_MSG_ERROR([You need at least version 2.0.1 of Twisted])
)

TWISTED_MODULE([twisted.names])
TWISTED_MODULE([twisted.web])

dnl Cortado
AC_ARG_WITH(cortado_prefix,
           AC_HELP_STRING(--with-cortado-prefix=<dir>, where cortado can be found))

CORTADO_PREFIX="$with_cortado_prefix"
AC_SUBST(CORTADO_PREFIX)

AC_CONFIG_FILES([env], [chmod +x env])
AC_CONFIG_FILES([bin/flumotion], [chmod +x bin/flumotion])
AC_CONFIG_FILES([bin/flumotion-admin], [chmod +x bin/flumotion-admin])
AC_CONFIG_FILES([bin/flumotion-admin-text], [chmod +x bin/flumotion-admin-text])
AC_CONFIG_FILES([bin/flumotion-command], [chmod +x bin/flumotion-command])
AC_CONFIG_FILES([bin/flumotion-inspect], [chmod +x bin/flumotion-inspect])
AC_CONFIG_FILES([bin/flumotion-job], [chmod +x bin/flumotion-job])
AC_CONFIG_FILES([bin/flumotion-launch], [chmod +x bin/flumotion-launch])
AC_CONFIG_FILES([bin/flumotion-manager], [chmod +x bin/flumotion-manager])
AC_CONFIG_FILES([bin/flumotion-nagios], [chmod +x bin/flumotion-nagios])
AC_CONFIG_FILES([bin/flumotion-rrdmon], [chmod +x bin/flumotion-rrdmon])
AC_CONFIG_FILES([bin/flumotion-tester], [chmod +x bin/flumotion-tester])
AC_CONFIG_FILES([bin/flumotion-worker], [chmod +x bin/flumotion-worker])
AC_CONFIG_FILES([bin/runtest], [chmod +x bin/runtest])
AC_CONFIG_FILES([misc/flumotion-verify-config], [chmod +x misc/flumotion-verify-config])

dnl output stuff
AC_OUTPUT(
Makefile
bin/Makefile
common/Makefile
data/Makefile
data/glade/Makefile
data/image/Makefile
data/image/16x16/Makefile
data/image/24x24/Makefile
data/image/wizard/Makefile
data/flumotion-admin.desktop
flumotion/Makefile
flumotion/admin/Makefile
flumotion/admin/assistant/Makefile
flumotion/admin/command/Makefile
flumotion/admin/gtk/Makefile
flumotion/admin/rrdmon/Makefile
flumotion/admin/text/Makefile
flumotion/common/Makefile
flumotion/component/Makefile
flumotion/component/base/Makefile
flumotion/component/bouncers/Makefile
flumotion/component/effects/Makefile
flumotion/component/effects/colorbalance/Makefile
flumotion/component/effects/volume/Makefile
flumotion/component/encoders/Makefile
flumotion/component/combiners/Makefile
flumotion/component/combiners/composite/Makefile
flumotion/component/combiners/switch/Makefile
flumotion/component/consumers/Makefile
flumotion/component/consumers/disker/Makefile
flumotion/component/consumers/gdp/Makefile
flumotion/component/consumers/httpstreamer/Makefile
flumotion/component/consumers/preview/Makefile
flumotion/component/consumers/shout2/Makefile
flumotion/component/converters/Makefile
flumotion/component/converters/pipeline/Makefile
flumotion/component/converters/overlay/Makefile
flumotion/component/misc/Makefile
flumotion/component/misc/httpserver/Makefile
flumotion/component/misc/porter/Makefile
flumotion/component/misc/repeater/Makefile
flumotion/component/muxers/Makefile
flumotion/component/plugs/Makefile
flumotion/component/plugs/cortado/Makefile
flumotion/component/plugs/cortado/cortado_location.py
flumotion/component/producers/Makefile
flumotion/component/producers/audiotest/Makefile
flumotion/component/producers/bttv/Makefile
flumotion/component/producers/firewire/Makefile
flumotion/component/producers/gdp/Makefile
flumotion/component/producers/icecast/Makefile
flumotion/component/producers/ivtv/Makefile
flumotion/component/producers/pipeline/Makefile
flumotion/component/producers/playlist/Makefile
flumotion/component/producers/rtsp/Makefile
flumotion/component/producers/screencast/Makefile
flumotion/component/producers/soundcard/Makefile
flumotion/component/producers/videotest/Makefile
flumotion/component/producers/webcam/Makefile
flumotion/component/producers/looper/Makefile
flumotion/component/producers/unixdomain/Makefile
flumotion/configure/Makefile
flumotion/configure/installed.py
flumotion/configure/uninstalled.py
flumotion/extern/Makefile
flumotion/extern/fdpass/Makefile
flumotion/extern/pytrayicon/Makefile
flumotion/job/Makefile
flumotion/launch/Makefile
flumotion/manager/Makefile
flumotion/monitor/Makefile
flumotion/monitor/nagios/Makefile
flumotion/project/Makefile
flumotion/service/Makefile
flumotion/scenario/Makefile
flumotion/scenario/live/Makefile
flumotion/scenario/ondemand/Makefile
flumotion/scenario/steps/Makefile
flumotion/test/Makefile
flumotion/tester/Makefile
flumotion/twisted/Makefile
flumotion/ui/Makefile
flumotion/worker/Makefile
flumotion/worker/checks/Makefile
conf/Makefile
doc/Makefile
doc/reference/Makefile
doc/man/Makefile
pkgconfig/Makefile
pkgconfig/flumotion.pc
pkgconfig/flumotion-uninstalled.pc
tests/Makefile
tests/integration/Makefile
flumotion.spec
po/Makefile.in
)

echo
echo "Building documentation: $enable_docs"
echo
echo "Now type \"make\" to build flumotion"

dnl echo
dnl echo "configure: *** Flumotion has been configured with support for the"
dnl echo "               following versions of GStreamer:"
dnl echo
dnl echo "    GStreamer 0.10: $GST_010_SUPPORTED"
dnl echo
dnl echo "If either version is disabled, check the configure output above to"
dnl echo "determine the cause of the problem, and re-run the configure"
dnl echo "script after installing the necessary dependencies."
dnl echo

dnl build triggers area
