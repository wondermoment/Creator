import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
import codex_local as local


class LocalCodexTests(unittest.TestCase):
    def test_environment_excludes_api_keys_and_provider_overrides(self):
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'secret', 'CODEX_HOME': 'wrong', 'OTHER_SECRET': 'private'}):
            env = local.environment('runtime-test')
        self.assertNotIn('OPENAI_API_KEY', env)
        self.assertNotIn('OTHER_SECRET', env)
        self.assertTrue(env['CODEX_HOME'].endswith('codex-local'))

    def test_unlisted_project_cannot_use_operator_login(self):
        with tempfile.TemporaryDirectory() as tmp:
            local.home(tmp).mkdir()
            (local.home(tmp) / 'allowed-projects.json').write_text('["one"]')
            with patch.object(local.subprocess, 'run') as run:
                self.assertFalse(local.availability(tmp, 'other')['available'])
                run.assert_not_called()

    def call(self, events, code=0):
        result = subprocess.CompletedProcess([], code, '\n'.join(json.dumps(e) for e in events), '')
        with tempfile.TemporaryDirectory() as tmp, patch.object(local, 'availability', return_value={'available': True}), patch.object(local, 'command', return_value=['codex']), patch.object(local.subprocess, 'run', return_value=result) as run:
            answer = local.generate(tmp, 'one', 'gpt-6-sol', [{'role': 'user', 'content': 'private fixture'}])
            args, kw = run.call_args
            self.assertNotIn('private fixture', ' '.join(args[0]))
            self.assertIn('private fixture', kw['input'])
            self.assertFalse(kw.get('shell', False))
            self.assertTrue(any(a.startswith('model_instructions_file=') for a in args[0]))
            self.assertIn('model_reasoning_effort="low"', args[0])
            for flag in ('--ephemeral', '--ignore-user-config', '--ignore-rules', 'features.shell_tool=false', 'features.apps=false'):
                self.assertIn(flag, args[0])
            return answer

    def test_complete_answer_usage_and_recovered_transient_error(self):
        text, meta = self.call([{'type': 'error', 'message': 'Reconnecting'}, {'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'OK'}}, {'type': 'turn.completed', 'usage': {'input_tokens': 12, 'output_tokens': 1}}])
        self.assertEqual(text, 'OK')
        self.assertEqual(meta['usage']['prompt_tokens'], 12)
        self.assertIsNone(meta['estimated_cost'])

    def test_failed_incomplete_and_tool_results_rejected(self):
        for events in ([{'type': 'turn.failed', 'error': {'message': 'sensitive'}}], [{'type': 'item.completed', 'item': {'type': 'agent_message', 'text': 'partial'}}], [{'type': 'item.completed', 'item': {'type': 'command_execution'}}]):
            with self.subTest(events=events), self.assertRaises(local.CodexLocalError) as caught:
                self.call(events)
            self.assertNotIn('sensitive', str(caught.exception))


if __name__ == '__main__':
    unittest.main()
