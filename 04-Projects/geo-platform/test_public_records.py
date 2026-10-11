import unittest
from unittest.mock import patch
from test_workflow import server


class PublicRecordsTests(unittest.TestCase):
    def test_nested_redaction_checks_permission_once_without_mutation(self):
        source = {'title': 'visible', 'prompt': 'secret', 'rows': [
            {'answer': 'ok', 'prompt_snapshot': {'hidden': True},
             'nested': [{'soul': 'secret', 'markdown': 'secret', 'n': 0}]},
            None, False, 'text', {'prompt_override': 'secret', 'soul_markdown': 'secret'}]}
        with patch.object(server, 'prompt_admin', return_value=False) as permission:
            result = server.public_records(source, {'user_id': 'reader'})
        permission.assert_called_once_with({'user_id': 'reader'})
        self.assertEqual(result, {'title': 'visible', 'rows': [
            {'answer': 'ok', 'nested': [{'n': 0}]}, None, False, 'text', {}]})
        self.assertEqual(source['prompt'], 'secret')
        self.assertEqual(source['rows'][0]['nested'][0]['soul'], 'secret')

    def test_permission_is_rechecked_after_revocation(self):
        source = {'prompt': 'secret', 'title': 'visible'}
        with patch.object(server, 'prompt_admin', side_effect=[True, False]) as permission:
            self.assertIs(server.public_records(source, {'user_id': 'operator'}), source)
            self.assertEqual(server.public_records(source, {'user_id': 'operator'}), {'title': 'visible'})
        self.assertEqual(permission.call_count, 2)


if __name__ == '__main__':
    unittest.main()
