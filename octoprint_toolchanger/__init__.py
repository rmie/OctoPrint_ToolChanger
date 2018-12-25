# coding=utf-8
from __future__ import absolute_import

import octoprint.plugin
import octoprint.settings
import flask
import cv2
import numpy as np
import urllib


class ToolChangerPlugin(octoprint.plugin.AssetPlugin,
                        octoprint.plugin.SettingsPlugin,
                        octoprint.plugin.TemplatePlugin,
                        octoprint.plugin.SimpleApiPlugin):

	def get_assets(self):
		return dict(
			js=['js/toolchanger.js']
		)

	def get_template_configs(self):
		return [
			dict(type='settings', custom_bindings=False),
			dict(type='sidebar', custom_bindings=False),
		]

	def get_settings_defaults(self):
		return dict(
			camera='http://localhost:8080/?action=snapshot'
		)

	def get_api_commands(self):
		# not yet implemented
		return dict(
			register=[],
			setcameraposition=[]
		)

	def is_api_adminonly(self):
		return False

	def _crop_image(self, image, size):
		center = np.array(size) / 2
		tl = np.array((image.shape[1], image.shape[0])) / 2 - center
		br = tl + size
		return image[tl[1]:br[1], tl[0]:br[0]], center

	def _estimate_focus(self, cropped, r1, r2):
		image, center = self._crop_image(cropped, (2 * r2, 2 * r2))
		# reduce image to size (r2,r2) and create grayscale image
		gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

		# gray = cv2.cvtColor(cropped, cv2.COLOR_BGR2GRAY)
		# laplacian is the 2nd derivitive, aka. the "edges" of the image
		laplacian = cv2.Laplacian(np.float32(gray), -1, ksize=3)

		# create an array filled with 1
		mask = np.full((2 * r2, 2 * r2), 1, np.uint8)
		# mask = np.full(gray.shape[0:2], 1, np.uint8)
		# fill the area between r1 and r2 with 0
		cv2.circle(mask, tuple(center), ((r2 + r1) / 2), (0, 0, 0), r2 - r1)
		masked = np.ma.masked_array(laplacian, mask=mask)

		# variance of the masked area is what we are after, the "sharper" the edges (focus)
		# the higher the variance. Maximizing this value can be used for Z calibration.
		return masked.var(), laplacian

	def _api_get_image(self, width, height, r1, r2):
		"""
		Retrieve an image from the inspection camera and crop it to the given size, add two circles as visual aides
		for the alignment process.

		For now, the focus is estimated as well, and inserted into the image.
		http://octopi.local:5000/api/plugin/toolchanger?image&width=588&height=441&apikey=...&r1=40&r2=100

		:param width:
		:param height:
		:param r1:
		:param r2:
		:return: flask.response containing the cropped image
		"""
		self._logger.debug('_api_command_image: {0} {1} {2} {3}'.format(width, height, r1, r2))

		camera = self._settings.get(['camera'])
		resp = urllib.urlopen(camera)
		bytes = np.asarray(bytearray(resp.read()), dtype='uint8')
		image = cv2.imdecode(bytes, cv2.IMREAD_COLOR)

		# crop the image down such that it fits into the viewport without scaling
		cropped, center = self._crop_image(image, (width, height))
		variance, _ = self._estimate_focus(cropped, r1, r2)
		self._logger.debug('_api_command_image: variance {0}'.format(variance))

		# add the circles
		cv2.circle(cropped, tuple(center), r1, (0, 255, 0), 1)
		cv2.circle(cropped, tuple(center), r2, (0, 255, 0), 1)

		font = cv2.FONT_HERSHEY_SIMPLEX
		cv2.putText(cropped, 'var:{0:.0f}'.format(variance), (0, 30), font, 1, (0, 255, 0), 2, cv2.LINE_AA)
		return cropped, center

	def on_api_get(self, request):
		response = None
		try:
			if request.args.has_key('image'):
				width = int(request.args['width'])
				height = int(request.args['height'])
				r1 = int(request.args['r1']) if request.args.has_key('r1') else 50
				r2 = int(request.args['r2']) if request.args.has_key('r2') else 100
				cropped, _ = self._api_get_image(width, height, r1, r2)
				bytes = cv2.imencode('.png', cropped)[1]
				response = flask.make_response(bytes.tostring())
				response.headers.set('Content-Type', 'image/png')
		except Exception as e:
			# bad practice, but nice for debugging
			response = flask.make_response(str(e))
			response.headers.set('Content-Type', 'text/plain')
		finally:
			return response

	def on_api_command(self, command, data):
		import flask
		if command == "register":
			# - save the current toolhead postion
			# - take an image of the tool for later reference
			pass
		elif command == "setcameraposition":
			# mostly for convenience, this should be used as tool position for uncalibrated tools
			pass

	def get_version(self):
		return self._plugin_version

	def get_update_information(self):
		return dict(
			toolchanger=dict(
				displayName="ToolChanger",
				displayVersion=self._plugin_version,
				type="github_release",
				user="rmie",
				repo="OctoPrint_ToolChanger",
				current=self._plugin_version,
				pip="https://github.com/rmie/OctoPrint_ToolChanger/archive/{target_version}.zip",
			)
		)


__plugin_name__ = "ToolChanger"
__author__ = "Roland Mieslinger <rolmie@gmail.com>"
__license__ = 'GNU Affero General Public License http://www.gnu.org/licenses/agpl.html'


def __plugin_load__():
	global __plugin_implementation__
	__plugin_implementation__ = ToolChangerPlugin()

	global __plugin_hooks__
	__plugin_hooks__ = {
		# "octoprint.plugin.softwareupdate.check_config": __plugin_implementation__.get_update_information
	}
