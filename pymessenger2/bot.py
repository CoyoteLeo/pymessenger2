import os
from enum import Enum

import json
import requests
from requests_toolbelt import MultipartEncoder

from pymessenger2 import utils
from pymessenger2.utils import AttrsEncoder

DEFAULT_API_VERSION = 2.6


class NotificationType(Enum):
    regular = "REGULAR"
    silent_push = "SILENT_PUSH"
    no_push = "NO_PUSH"


class Bot(object):
    def __init__(self,
                 access_token,
                 api_version=DEFAULT_API_VERSION,
                 app_secret=None):
        """
            @required:
                access_token
            @optional:
                api_version
                app_secret
        """
        self.api_version = api_version
        self.app_secret = app_secret
        self.graph_url = 'https://graph.facebook.com/v{0}'.format(
            self.api_version)
        self.access_token = access_token

    @property
    def auth_args(self):
        if not hasattr(self, '_auth_args'):
            auth = {'access_token': self.access_token}
            if self.app_secret is not None:
                appsecret_proof = utils.generate_appsecret_proof(
                    self.access_token, self.app_secret)
                auth['appsecret_proof'] = appsecret_proof
            self._auth_args = auth
        return self._auth_args

    def add_domains_to_whitelist(self, domains):
        payload = {
            "whitelisted_domains": domains
        }

        request_endpoint = '{0}/me/messenger_profile'.format(self.graph_url)
        response = requests.post(
            request_endpoint,
            params=self.auth_args,
            json=payload
        )
        result = response.json()
        return result

    def send_recipient(self,
                       recipient_id,
                       payload,
                       notification_type=NotificationType.regular.value):
        payload['recipient'] = {'id': recipient_id}
        payload['notification_type'] = notification_type
        return self.send_raw(payload)

    def send_message(self,
                     recipient_id,
                     message,
                     notification_type=NotificationType.regular.value):
        return self.send_recipient(recipient_id, {'message': message},
                                   notification_type)

    def send_attachment(self,
                        recipient_id,
                        attachment_type,
                        attachment_path,
                        notification_type=NotificationType.regular.value):
        """Send an attachment to the specified recipient using local path.
        Input:
            recipient_id: recipient id to send to
            attachment_type: type of attachment (image, video, audio, file)
            attachment_path: Path of attachment
        Output:
            Response from API as <dict>
        """
        with open(attachment_path, 'rb') as f:
            attachment_filename = os.path.basename(attachment_path)
            if attachment_type != 'file':
                attachment_ext = attachment_filename.split('.')[1]
                content_type = attachment_type + '/' + attachment_ext # eg: audio/mp3
            else:
                content_type = ''
            payload = {
                'recipient': json.dumps({
                    'id': recipient_id
                }),
                'notification_type': notification_type,
                'message': json.dumps({
                    'attachment': {
                        'type': attachment_type,
                        'payload': {}
                    }
                }),
                'filedata':
                (attachment_filename, f, content_type)
            }
            multipart_data = MultipartEncoder(payload)
            multipart_header = {'Content-Type': multipart_data.content_type}
            request_endpoint = '{0}/me/messages'.format(self.graph_url)
            return requests.post(
                request_endpoint,
                data=multipart_data,
                params=self.auth_args,
                headers=multipart_header).json()

    def send_attachment_url(self,
                            recipient_id,
                            attachment_type,
                            attachment_url,
                            notification_type=NotificationType.regular.value):
        """Send an attachment to the specified recipient using URL.
        Input:
            recipient_id: recipient id to send to
            attachment_type: type of attachment (image, video, audio, file)
            attachment_url: URL of attachment
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            'attachment': {
                'type': attachment_type,
                'payload': {
                    'url': attachment_url
                }
            }
        }, notification_type)

    def send_text_message(self,
                          recipient_id,
                          message,
                          notification_type=NotificationType.regular.value):
        """Send text messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/text-message
        Input:
            recipient_id: recipient id to send to
            message: message to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {'text': message},
                                 notification_type)

    def send_generic_message(self,
                             recipient_id,
                             elements,
                             image_aspect_ratio='horizontal',
                             notification_type=NotificationType.regular.value):
        """Send generic messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/generic-template
        Input:
            recipient_id: recipient id to send to
            elements: generic message elements to send
            image_aspect_ratio: 'horizontal' (default) or 'square'
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "generic",
                    "image_aspect_ratio": image_aspect_ratio,
                    "elements": elements
                }
            }
        }, notification_type)
    
    def send_quick_reply(self,
                         recipient_id,
                         message,
                         buttons,
                         notification_type=NotificationType.regular.value):
        """Quick Replies provide a way to present buttons in a message.
        https://developers.facebook.com/docs/messenger-platform/send-messages/quick-replies
        Input:
            recipient_id: recipient id to send to
            message: message to send
            buttons: buttons to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
                'text': message,
                'quick_replies': buttons
                }, notification_type)
    
    def send_button_message(self,
                            recipient_id,
                            text,
                            buttons,
                            notification_type=NotificationType.regular.value):
        """Send text messages to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/button-template
        Input:
            recipient_id: recipient id to send to
            text: text of message to send
            buttons: buttons to send
        Output:
            Response from API as <dict>
        """
        return self.send_message(recipient_id, {
            "attachment": {
                "type": "template",
                "payload": {
                    "template_type": "button",
                    "text": text,
                    "buttons": buttons
                }
            }
        }, notification_type)

    def send_action(self,
                    recipient_id,
                    action,
                    notification_type=NotificationType.regular.value):
        """Send typing indicators or send read receipts to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/sender-actions

        Input:
            recipient_id: recipient id to send to
            action: action type (mark_seen, typing_on, typing_off)
        Output:
            Response from API as <dict>
        """
        return self.send_recipient(recipient_id, {'sender_action': action},
                                   notification_type)

    def send_image(self,
                   recipient_id,
                   image_path,
                   notification_type=NotificationType.regular.value):
        """Send an image to the specified recipient.
        Image must be PNG or JPEG or GIF (more might be supported).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment
        Input:
            recipient_id: recipient id to send to
            image_path: path to image to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "image", image_path,
                                    notification_type)

    def send_image_url(self,
                       recipient_id,
                       image_url,
                       notification_type=NotificationType.regular.value):
        """Send an image to specified recipient using URL.
        Image must be PNG or JPEG or GIF (more might be supported).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/image-attachment
        Input:
            recipient_id: recipient id to send to
            image_url: url of image to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "image", image_url,
                                        notification_type)

    def send_audio(self,
                   recipient_id,
                   audio_path,
                   notification_type=NotificationType.regular.value):
        """Send audio to the specified recipient.
        Audio must be MP3 or WAV
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/audio-attachment
        Input:
            recipient_id: recipient id to send to
            audio_path: path to audio to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "audio", audio_path,
                                    notification_type)

    def send_audio_url(self,
                       recipient_id,
                       audio_url,
                       notification_type=NotificationType.regular.value):
        """Send audio to specified recipient using URL.
        Audio must be MP3 or WAV
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/audio-attachment
        Input:
            recipient_id: recipient id to send to
            audio_url: url of audio to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "audio", audio_url,
                                        notification_type)

    def send_video(self,
                   recipient_id,
                   video_path,
                   notification_type=NotificationType.regular.value):
        """Send video to the specified recipient.
        Video should be MP4 or MOV, but supports more (https://www.facebook.com/help/218673814818907).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/video-attachment
        Input:
            recipient_id: recipient id to send to
            video_path: path to video to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "video", video_path,
                                    notification_type)

    def send_video_url(self,
                       recipient_id,
                       video_url,
                       notification_type=NotificationType.regular.value):
        """Send video to specified recipient using URL.
        Video should be MP4 or MOV, but supports more (https://www.facebook.com/help/218673814818907).
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/video-attachment
        Input:
            recipient_id: recipient id to send to
            video_url: url of video to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "video", video_url,
                                        notification_type)

    def send_file(self,
                  recipient_id,
                  file_path,
                  notification_type=NotificationType.regular.value):
        """Send file to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/file-attachment
        Input:
            recipient_id: recipient id to send to
            file_path: path to file to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment(recipient_id, "file", file_path,
                                    notification_type)

    def send_file_url(self,
                      recipient_id,
                      file_url,
                      notification_type=NotificationType.regular.value):
        """Send file to the specified recipient.
        https://developers.facebook.com/docs/messenger-platform/send-api-reference/file-attachment
        Input:
            recipient_id: recipient id to send to
            file_url: url of file to be sent
        Output:
            Response from API as <dict>
        """
        return self.send_attachment_url(recipient_id, "file", file_url,
                                        notification_type)

    def get_user_info(self, recipient_id, fields=None):
        """Getting information about the user
        https://developers.facebook.com/docs/messenger-platform/user-profile
        Input:
          recipient_id: recipient id to send to
        Output:
          Response from API as <dict>
        """
        params = {}
        if fields is not None and isinstance(fields, (list, tuple)):
            params['fields'] = ",".join(fields)

        params.update(self.auth_args)

        request_endpoint = '{0}/{1}'.format(self.graph_url, recipient_id)
        response = requests.get(request_endpoint, params=params)
        if response.status_code == 200:
            return response.json()

        return None

    def send_raw(self, payload):
        request_endpoint = '{0}/me/messages'.format(self.graph_url)
        response = requests.post(
            request_endpoint,
            params=self.auth_args,
            data=json.dumps(payload, cls=AttrsEncoder),
            headers={'Content-Type': 'application/json'})
        result = response.json()
        return result

    def _send_payload(self, payload):
        """ Deprecated, use send_raw instead """
        return self.send_raw(payload)
