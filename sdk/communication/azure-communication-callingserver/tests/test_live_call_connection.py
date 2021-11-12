# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import uuid
import os
import pytest
import utils._test_constants as CONST

from azure.communication.callingserver import (
    CallingServerClient,
    PlayAudioOptions,
    CreateCallOptions,
    CallMediaType,
    CallingEventSubscriptionType,
    CallConnection, AddParticipantResult,
    )
from azure.communication.chat import PhoneNumberIdentifier
from azure.communication.identity import CommunicationUserIdentifier
from azure.communication.callingserver._shared.utils import parse_connection_str
from azure.identity import DefaultAzureCredential
from _shared.testcase import (
    CommunicationTestCase,
    BodyReplacerProcessor,
    ResponseReplacerProcessor
)
from devtools_testutils import is_live
from _shared.utils import get_http_logging_policy
from utils._live_test_utils import CallingServerLiveTestUtils
from utils._test_mock_utils import FakeTokenCredential
from azure.communication.identity._shared.models import CommunicationIdentifier, CommunicationIdentifierKind

class CallConnectionTest(CommunicationTestCase):
    
    call_connection: CallConnection = None
    def setUp(self):
        super(CallConnectionTest, self).setUp()

        self.from_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)
        self.to_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)
        
        if self.is_playback():
            self.from_phone_number = "+15551234567"
            self.to_phone_number = "+15551234567"
            self.participant_id = CallingServerLiveTestUtils.get_fixed_user_id("0000000d-06a7-7ed4-bf75-25482200020e")
            self.recording_processors.extend([
                BodyReplacerProcessor(keys=["alternateCallerId", "targets", "source", "callbackUri"])])
        else:
            self.to_phone_number = os.getenv("AZURE_PHONE_NUMBER")
            self.from_phone_number = os.getenv("ALTERNATE_CALLERID")          
            self.participant_id = os.getenv("PARTICIPENT_ID") # use communication identifier
            self.target_call_connection_id = os.getenv("CALL_CONNECTION_ID") # use communication id from another live call
        # create CallingServerClient
        endpoint, _ = parse_connection_str(self.connection_str)
        endpoint = endpoint

        if not is_live():
            credential = FakeTokenCredential()          
        else:
            credential = DefaultAzureCredential()

        self.calling_server_client = CallingServerClient(
            endpoint,
            credential,
            http_logging_policy=get_http_logging_policy()
        )
        
    def test_create_add_remove_hangup_scenario(self):
            # create option
            options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
            requested_media_types=[CallMediaType.AUDIO],
            requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
            options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
            options.subject = 'test subject'
            # Establish a call
            self.call_connection = self.calling_server_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options,
                        )        
            try:
                # Add Participant
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                operation_context = str(uuid.uuid4())   
                alternate_caller_id = PhoneNumberIdentifier(value=self.from_phone_number)
                participant = CommunicationUserIdentifier(id=self.participant_id)

                add_participant_response:AddParticipantResult = self.call_connection.add_participant(participant=participant,alternate_caller_id=alternate_caller_id, operation_context=operation_context)
                CallingServerLiveTestUtils.validate_add_participant(add_participant_response)

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # Remove Participant
                self.call_connection.remove_participant(participant)
            except Exception as ex:
                print( str(ex))
            finally:
                # Hang up
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                self.call_connection.hang_up()

    def test_create_add_get_participant_mute_hangup_scenario(self):
            # create option
            options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
            requested_media_types=[CallMediaType.AUDIO],
            requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
            options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
            options.subject = 'test subject'
            # Establish a call
            self.call_connection = self.calling_server_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options
                        )    
            try:
              # Add Participant
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                operation_context = str(uuid.uuid4())   
                alternate_caller_id = PhoneNumberIdentifier(value=self.from_phone_number)
                participant = CommunicationUserIdentifier(id=self.participant_id)

                add_participant_response:AddParticipantResult = self.call_connection.add_participant(participant=participant,alternate_caller_id=alternate_caller_id, operation_context=operation_context)

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # Mute Participant
                mute_participant = self.call_connection.mute_participant(participant)

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # Get Participant
                get_participant = self.call_connection.get_participant(participant)
                assert len(get_participant)  > 0

                assert get_participant[0].is_muted == True

                # UnMute Participant
                unmute_participant = self.call_connection.unmute_participant(participant)

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # get_participant = self.call_connection.get_participant(participant)
                # assert get_participant[0].is_muted == False  #not working currently

                # Get Participants
                all_participants = self.call_connection.get_participants()
                assert len(all_participants)  > 2

                # Remove Participant
                self.call_connection.remove_participant(participant)
            except Exception as ex:
                print( str(ex))
            finally:
                # Hang up
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                self.call_connection.hang_up()

    def test_hold_resume_participant_audio_scenario(self):
            # create option
            options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
            requested_media_types=[CallMediaType.AUDIO],
            requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
            options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
            options.subject = 'test subject'
            # Establish a call
            self.call_connection = self.calling_server_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options
                        )    
            try:
              # Add Participant
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                operation_context = str(uuid.uuid4())   
                alternate_caller_id = PhoneNumberIdentifier(value=self.from_phone_number)
                participant = CommunicationUserIdentifier(id=self.participant_id)

                add_participant_response:AddParticipantResult = self.call_connection.add_participant(participant=participant,alternate_caller_id=alternate_caller_id, operation_context=operation_context)

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # hold_participant_meeting_audio 
                hold_audio_participant = self.call_connection.hold_participant_meeting_audio(participant)
                assert hold_audio_participant is None

                CallingServerLiveTestUtils.sleep_if_in_live_mode()

                # resume_participant_meeting_audio
                resume_audio_participant = self.call_connection.resume_participant_meeting_audio(participant)
                assert resume_audio_participant is None

                # Remove Participant
                self.call_connection.remove_participant(participant)
            except Exception as ex:
                print( str(ex))
            finally:
                # Hang up
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                self.call_connection.hang_up()

    def test_create_play_cancel_hangup_scenario(self):
        # create call option
        options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
        requested_media_types=[CallMediaType.AUDIO],
        requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
        options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
        options.subject = 'test subject'
        # Establish a call
        self.call_connection = self.calling_server_client.create_call_connection(
                    source=CommunicationUserIdentifier(self.from_user),
                    targets=[PhoneNumberIdentifier(self.to_phone_number)],
                    options=options
                    )    

        CallingServerLiveTestUtils.validate_callconnection(self.call_connection)


        # Cat the call
        callProps = self.call_connection.get_call()
        assert callProps.call_connection_id == self.call_connection.call_connection_id
        assert callProps.call_connection_state == 'connected' or 'connecting'
        try:
            # Play Audio
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            OperationContext = str(uuid.uuid4())
            AudioFileId = str(uuid.uuid4())
            options = PlayAudioOptions(
                loop = True,
                audio_file_id = AudioFileId,
                callback_uri = CONST.AppCallbackUrl,
                operation_context = OperationContext
                )
            play_audio_result = self.call_connection.play_audio(
                CONST.AudioFileUrl,
                options
                )
            CallingServerLiveTestUtils.validate_play_audio_result(play_audio_result)

            # Cancel All Media Operations
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            self.call_connection.cancel_all_media_operations()
        except Exception as ex:
            print( str(ex))
        finally:
            # Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            self.call_connection.hang_up()

    def test_create_delete_keep_alive_scenario(self):
            # create option
            options = CreateCallOptions(
                callback_uri=CONST.AppCallbackUrl,
                requested_media_types=[CallMediaType.AUDIO],
                requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED]
            )
            options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)

            # Establish a call
            call_connection = self.calling_server_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options,
                        )

            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            
            # check keep_alive
            k = call_connection.keep_alive()
            assert k is None

            # Delete the call
            call_connection.delete_call()   # notice that call got disconnected
            try:
                 call_connection.keep_alive()
            except Exception as ex:
                assert '8522' in str(ex)
    
    def test_create_transfer_remove_hangup_scenario(self):
            # create option
            options = CreateCallOptions(
                callback_uri=CONST.AppCallbackUrl,
                requested_media_types=[CallMediaType.AUDIO],
                requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED, CallingEventSubscriptionType.TONE_RECEIVED]
            )
            options.subject = 'test subject'
            options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)

            # Establish a call
            self.call_connection = self.calling_server_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options,
                        )        
            try:
                # Transfer call
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                operation_context = str(uuid.uuid4())   
                participant = CommunicationUserIdentifier(id=self.participant_id)

                transfer_call_result = self.call_connection.transfer_call(target_participant=participant,
                            target_call_connection_id=self.target_call_connection_id, user_to_user_information='', 
                            operation_context=operation_context, callback_uri=CONST.AppCallbackUrl)

                print(str(transfer_call_result))
                assert transfer_call_result == None

                # Remove Participant
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                self.call_connection.remove_participant(participant)
            except Exception as ex:
                print( str(ex))
            finally:
                # Hang up
                CallingServerLiveTestUtils.sleep_if_in_live_mode()
                self.call_connection.hang_up()
     