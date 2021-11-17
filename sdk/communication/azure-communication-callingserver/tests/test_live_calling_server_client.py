# -------------------------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# Licensed under the MIT License. See License.txt in the project root for
# license information.
# --------------------------------------------------------------------------
import os, uuid, pytest
from time import sleep
import utils._test_constants as CONST
from azure.communication.callingserver import (
    CallingServerClient,
    PlayAudioOptions,
    CommunicationUserIdentifier,
    GroupCallLocator,
    CallMediaType,
    CallingEventSubscriptionType,
    ServerCallLocator,CreateCallOptions
    )
from azure.communication.chat import PhoneNumberIdentifier
from azure.communication.callingserver._shared.utils import parse_connection_str
from azure.identity import DefaultAzureCredential
from _shared.testcase import (
    CommunicationTestCase,
    BodyReplacerProcessor,
    ResponseReplacerProcessor
)
from devtools_testutils import is_live
from _shared.utils import get_http_logging_policy
from utils._live_test_utils import CallingServerLiveTestUtils, RequestReplacerProcessor
from utils._test_mock_utils import FakeTokenCredential

from azure.core.exceptions import (
    HttpResponseError
)

class ServerCallTest(CommunicationTestCase):

    def setUp(self):
        super(ServerCallTest, self).setUp()

        self.from_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)
        self.to_user = CallingServerLiveTestUtils.get_new_user_id(self.connection_str)

        if self.is_playback():
            self.from_phone_number = "+18334241267"
            self.to_phone_number = "+918559859399"
            self.recording_processors.extend([
                BodyReplacerProcessor(keys=["alternateCallerId", "targets", "source", "callbackUri"])])
        else:
            # self.to_phone_number = os.getenv("AZURE_PHONE_NUMBER")
            # self.from_phone_number = os.getenv("ALTERNATE_CALLERID")
            # self.participant_id = os.getenv("PARTICIPENT_ID") # use communication identifier
            self.recording_processors.extend([
                BodyReplacerProcessor(keys=["alternateCallerId", "targets", "source", "callbackUri"]),
                ResponseReplacerProcessor(keys=[self._resource_name])])

        # create CallingServerClient
        endpoint, _ = parse_connection_str(self.connection_str)
        self.endpoint = endpoint

        if not is_live():
            credential = FakeTokenCredential()
        else:
            credential = DefaultAzureCredential()

        self.callingserver_client = CallingServerClient(
            self.endpoint,
            credential,
            http_logging_policy=get_http_logging_policy()
        )

    def test_join_play_cancel_hangup_scenario(self):
        # create GroupCalls
        # group_id = CallingServerLiveTestUtils.get_group_id("test_join_play_cancel_hangup_scenario")
        group_id='5acb4690-47a5-11ec-87bb-bf2fa49f5208'

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_join_play_cancel_hangup_scenario"))])

        call_connections = CallingServerLiveTestUtils.create_group_calls(
            self.callingserver_client,
            group_id,
            self.from_user,
            self.to_user,
            CONST.CALLBACK_URI
            )

        try:
            # Play Audio
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            OperationContext = str(uuid.uuid4())
            options = PlayAudioOptions(
                loop = True,
                audio_file_id = str(uuid.uuid4()),
                callback_uri = CONST.AppCallbackUrl,
                operation_context = OperationContext
                )
            play_audio_result = self.callingserver_client.play_audio(
                GroupCallLocator(group_id),
                CONST.AudioFileUrl,
                options
                )
            CallingServerLiveTestUtils.validate_play_audio_result(play_audio_result)

       
            # cancel_media_operation not working
            self.callingserver_client.cancel_media_operation(
                call_locator=GroupCallLocator(group_id), 
                media_operation_id=play_audio_result.operation_id )

            # Cancel Prompt Audio
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.cancel_all_media_operations_for_group_call(call_connections)
        except Exception as ex:
            print(str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections(call_connections)
   
    def test_create_join_hangup_scenario(self):
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_join_hangup_scenario")
        participant = CallingServerLiveTestUtils.get_fixed_user_id("0000000d-06a7-7ed4-bf75-25482200020e")
        self.recording_processors.extend([
        RequestReplacerProcessor(keys=group_id,
            replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_join_hangup_scenario"))])

        call_connections = CallingServerLiveTestUtils.create_group_calls(
            self.callingserver_client,
            group_id,
            self.from_user,
            self.to_user,
            CONST.CALLBACK_URI
            )

        try:
            assert call_connections[0].call_connection_id is not None

            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.cancel_all_media_operations_for_group_call(call_connections)
        except Exception as ex:
            print(str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections(call_connections)

    def test_add_participant_using_calling_server_client(self):
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_join_hangup_scenario")
        self.recording_processors.extend([
        RequestReplacerProcessor(keys=group_id,
            replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_join_hangup_scenario"))])

        call_locator = GroupCallLocator('d2bc2300-479f-11ec-a1e1-bd55c8631198')
        # call_locator = ServerCallLocator('aHR0cHM6Ly9jb252LWpwd2UtMDguY29udi5za3lwZS5jb206NDQzL2NvbnYvbjBSc2FTemZLRXlrU2RoNVU1ampoQT9pPTE5JmU9NjM3NzIyNjE0OTc5OTUwOTgx')
        # start_call_recording_result = self.callingserver_client.start_recording(call_locator, CONST.CALLBACK_URI)

        try:
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            OperationContext = str(uuid.uuid4())
            participant = CommunicationUserIdentifier(id=self.participant_id)

            # not working currently 
            # invalid arguments
            add_participant_result = self.callingserver_client.add_participant(
                call_locator=call_locator,
                participant=participant,
                callback_uri=CONST.CALLBACK_URI,
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)

            CallingServerLiveTestUtils.sleep_if_in_live_mode()

        except Exception as ex:
            print(str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            # CallingServerLiveTestUtils.clean_up_connections(call_connections)

    def test_add_participant_using_call_connection(self):
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_join_hangup_scenario")
        self.recording_processors.extend([
        RequestReplacerProcessor(keys=group_id,
            replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_join_hangup_scenario"))])

        call_connections = CallingServerLiveTestUtils.create_group_calls(
            self.callingserver_client,
            group_id,
            self.from_user,
            self.to_user,
            CONST.CALLBACK_URI
            )

        call_connection = self.callingserver_client.get_call_connection(call_connections[0].call_connection_id)

        try:
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            OperationContext = str(uuid.uuid4())
            participant = CommunicationUserIdentifier(id=self.participant_id)
            add_participant_result = call_connection.add_participant(
                participant=participant,
                alternate_caller_id=None,
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)

            CallingServerLiveTestUtils.sleep_if_in_live_mode()

            # hold_participant_meeting_audio not working
            # hold_participant_meeting_audio_result= self.callingserver_client.hold_participant_meeting_audio(
            #     call_locator= GroupCallLocator(group_id),
            #     participant=participant
            #     )

            CallingServerLiveTestUtils.sleep_if_in_live_mode()

             # resume_participant_meeting_audio not working
            # resume_participant_meeting_audio_result= self.callingserver_client.resume_participant_meeting_audio(
            #     call_locator= GroupCallLocator(group_id),
            #     participant=participant
            #     )


            # Get Participant
            participant = CommunicationUserIdentifier(id=self.participant_id)
            get_participant = self.callingserver_client.get_participant(GroupCallLocator(group_id), participant)
            assert len(get_participant)  > 0

            CallingServerLiveTestUtils.cancel_all_media_operations_for_group_call(call_connections)
        except Exception as ex:
            print(str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections(call_connections)

    def test_play_audio_to_participant(self):
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_add_remove_hangup_scenario")

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_add_remove_hangup_scenario"))])

        options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
            requested_media_types=[CallMediaType.AUDIO],
            requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
        options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
        options.subject = 'test subject'

        call_connection = self.callingserver_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options,
                        )

        try:
            # Add Participant
            operation_context = str(uuid.uuid4())
            alternate_caller_id = PhoneNumberIdentifier(value=self.from_phone_number)
            participant = CommunicationUserIdentifier(id=self.participant_id)

            add_participant_response = call_connection.add_participant(participant=participant,alternate_caller_id=alternate_caller_id, operation_context=operation_context)
            CallingServerLiveTestUtils.validate_add_participant(add_participant_response)

            options = PlayAudioOptions(
                loop = True,
                audio_file_id = str(uuid.uuid4()),
                callback_uri = CONST.AppCallbackUrl,
                operation_context = str(uuid.uuid4())
                )

            # play_audio_to_participant #not working currently
            play_audio_to_participant_result = self.callingserver_client.play_audio_to_participant(
             call_locator=GroupCallLocator(group_id),
             participant=participant, 
             audio_file_uri = CONST.AudioFileUrl,
             play_audio_options=options)

            CallingServerLiveTestUtils.sleep_if_in_live_mode()

            # pending to test cancel_participant_media_operation because play_audio_to_participant is not working currently
            cancel_participant_media_operation_result = self.callingserver_client.cancel_participant_media_operation(
                call_locator=GroupCallLocator(group_id),
                participant=participant,
                media_operation_id=play_audio_to_participant_result.media_operation_id
            )

            # Remove Participant
            call_connection.remove_participant(participant)

        except Exception as ex:
            print( str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections([call_connection])


    def test_add_participant_using_create_call_connection(self): #10
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_add_remove_hangup_scenario")

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_add_remove_hangup_scenario"))])

        options = CreateCallOptions(callback_uri=CONST.AppCallbackUrl,
            requested_media_types=[CallMediaType.AUDIO],
            requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])
        options.alternate_Caller_Id = PhoneNumberIdentifier(self.from_phone_number)
        options.subject = 'test subject'

        call_connection = self.callingserver_client.create_call_connection(
                        source=CommunicationUserIdentifier(self.from_user),
                        targets=[PhoneNumberIdentifier(self.to_phone_number)],
                        options=options,
                        )

        try:
            # Add Participant
            operation_context = str(uuid.uuid4())
            alternate_caller_id = PhoneNumberIdentifier(value=self.from_phone_number)
            participant = CommunicationUserIdentifier(id=self.participant_id)

            add_participant_response = call_connection.add_participant(participant=participant,alternate_caller_id=alternate_caller_id, operation_context=operation_context)
            CallingServerLiveTestUtils.validate_add_participant(add_participant_response)

            # answer_call not working
            # self.callingserver_client.answer_call(incoming_call_context='dummyIncomingCallContext', callback_uri=CONST.AppCallbackUrl, 
            # requested_media_types=[CallMediaType.AUDIO], requested_call_events=[CallingEventSubscriptionType.PARTICIPANTS_UPDATED])

            CallingServerLiveTestUtils.sleep_if_in_live_mode()

            # Remove Participant
            call_connection.remove_participant(participant)

        except Exception as ex:
            print( str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections([call_connection])

    def test_create_add_remove_hangup_scenario(self):
        # create GroupCalls
        group_id = CallingServerLiveTestUtils.get_group_id("test_create_add_remove_hangup_scenario")

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_create_add_remove_hangup_scenario"))])

        call_connections = CallingServerLiveTestUtils.create_group_calls(
            self.callingserver_client,
            group_id,
            self.from_user,
            self.to_user,
            CONST.CALLBACK_URI
            )

        try:
            # Add Participant
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            OperationContext = str(uuid.uuid4())
            participant = CommunicationUserIdentifier(id=self.participant_id)
            added_participant = CallingServerLiveTestUtils.get_fixed_user_id("0000000d-06a7-7ed4-bf75-25482200020e")
            add_participant_result = self.callingserver_client.add_participant(
                call_locator=GroupCallLocator(group_id),
                participant=participant,
                callback_uri=CONST.AppCallbackUrl,
                alternate_caller_id=None,
                operation_context=OperationContext
                )
            CallingServerLiveTestUtils.validate_add_participant(add_participant_result)

            # Remove Participant
            participant_id=add_participant_result.participant_id
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            self.callingserver_client.remove_participant(
                GroupCallLocator(group_id),
                CommunicationUserIdentifier(added_participant)
                )
        except Exception as ex:
            print( str(ex))
        finally:
            # Clean up/Hang up
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            CallingServerLiveTestUtils.clean_up_connections(call_connections)

    def test_run_all_client_functions(self):
        group_id = CallingServerLiveTestUtils.get_group_id("test_run_all_client_functions")

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_run_all_client_functions"))])

        try:
            start_call_recording_result = self.callingserver_client.start_recording(GroupCallLocator(group_id), CONST.CALLBACK_URI)
            recording_id = start_call_recording_result.recording_id

            
            # Get Participants
            all_participants = self.callingserver_client.get_participants(GroupCallLocator(group_id))
            assert len(all_participants)  > 0

            assert recording_id is not None
            CallingServerLiveTestUtils.sleep_if_in_live_mode()

            recording_state = self.callingserver_client.get_recording_properities(recording_id)
            assert recording_state.recording_state == "active"

            self.callingserver_client.pause_recording(recording_id)
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            recording_state = self.callingserver_client.get_recording_properities(recording_id)
            assert recording_state.recording_state == "inactive"

            self.callingserver_client.resume_recording(recording_id)
            CallingServerLiveTestUtils.sleep_if_in_live_mode()
            recording_state = self.callingserver_client.get_recording_properities(recording_id)
            assert recording_state.recording_state == "active"

            self.callingserver_client.stop_recording(recording_id)

        except Exception as ex:
            print(str(ex))

    def test_start_recording_using_from_connection_string(self):
        group_id = CallingServerLiveTestUtils.get_group_id("test_run_all_client_functions")
        client = CallingServerClient.from_connection_string(self.connection_str)

        if self.is_live:
            self.recording_processors.extend([
            RequestReplacerProcessor(keys=group_id,
                replacement=CallingServerLiveTestUtils.get_playback_group_id("test_run_all_client_functions"))])

        try:
            start_call_recording_result = client.start_recording(GroupCallLocator(group_id), CONST.CALLBACK_URI)
            recording_id = start_call_recording_result.recording_id

            assert recording_id is not None

            self.callingserver_client.stop_recording(recording_id)

        except Exception as ex:
            print(str(ex))


    def test_start_recording_fails(self):
        invalid_server_call_id = "aHR0cHM6Ly9jb252LXVzd2UtMDkuY29udi5za3lwZS5jb20vY29udi9EZVF2WEJGVVlFV1NNZkFXYno2azN3P2k9MTEmZT02Mzc1NzIyMjk0Mjc0NTI4Nzk="

        with self.assertRaises(HttpResponseError):
            self.callingserver_client.start_recording(GroupCallLocator(invalid_server_call_id), CONST.CALLBACK_URI)

    def test_delete_success(self):
        delete_url = CallingServerLiveTestUtils.get_delete_url()
        delete_response = self.callingserver_client.delete_recording(delete_url)
        assert delete_response is not None
        assert delete_response.status_code == 200

    def test_delete_content_not_exists(self):
        delete_url = CallingServerLiveTestUtils.get_invalid_delete_url()
        with self.assertRaises(HttpResponseError):
            self.callingserver_client.delete_recording(delete_url)

    def test_delete_content_unauthorized(self):       
        delete_url = CallingServerLiveTestUtils.get_delete_url()       
        unauthorized_client = CallingServerClient.from_connection_string("endpoint=https://test.communication.azure.com/;accesskey=1234")
        with self.assertRaises(HttpResponseError):
            unauthorized_client.delete_recording(delete_url)
	
