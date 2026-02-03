#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import tempfile
import unittest


ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)


from server.mypm.app import create_app
from server.mypm.config import Config


class SmokeTestAPI(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(prefix='pilotdeck-smoke-')
        db_file = os.path.join(self._tmp.name, 'pm.db')

        cfg = Config()
        cfg.DB_FILE = db_file
        self.app = create_app(cfg)
        self.client = self.app.test_client()

    def tearDown(self):
        self._tmp.cleanup()

    def _create_project(self):
        resp = self.client.post('/api/projects', json={'name': 'Smoke Project'})
        self.assertEqual(resp.status_code, 201, resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertTrue(body.get('success'), body)
        return body['data']

    def test_patch_concurrency(self):
        proj = self._create_project()
        pid = proj['id']

        resp_get = self.client.get(f'/api/projects/{pid}')
        self.assertEqual(resp_get.status_code, 200, resp_get.get_data(as_text=True))
        cur = resp_get.get_json()['data']

        resp_conflict = self.client.patch(
            f'/api/projects/{pid}',
            json={'ifUpdatedAt': 'not-a-timestamp', 'status': 'in-progress'},
        )
        self.assertEqual(resp_conflict.status_code, 409, resp_conflict.get_data(as_text=True))

        resp_ok = self.client.patch(
            f'/api/projects/{pid}',
            json={'ifUpdatedAt': cur['updatedAt'], 'status': 'in-progress'},
        )
        self.assertEqual(resp_ok.status_code, 200, resp_ok.get_data(as_text=True))
        patched = resp_ok.get_json()['data']
        self.assertEqual(patched['status'], 'in-progress')
        self.assertNotEqual(patched['updatedAt'], cur['updatedAt'])

    def test_agent_actions_happy_path_and_idempotency(self):
        proj = self._create_project()
        pid = proj['id']

        resp_get = self.client.get(f'/api/projects/{pid}')
        self.assertEqual(resp_get.status_code, 200, resp_get.get_data(as_text=True))
        cur = resp_get.get_json()['data']

        payload = {
            'agentId': 'smoke',
            'actions': [
                {
                    'id': 'act-smoke-001',
                    'projectId': pid,
                    'type': 'set_progress',
                    'params': {'progress': 10},
                    'ifUpdatedAt': cur['updatedAt'],
                }
            ],
        }

        resp = self.client.post('/api/agent/actions', json=payload)
        self.assertEqual(resp.status_code, 200, resp.get_data(as_text=True))
        body = resp.get_json()
        self.assertTrue(body.get('success'), body)
        self.assertTrue(body['data']['changed'], body)
        self.assertTrue(body['data'].get('lastUpdated'), body)

        r0 = body['data']['results'][0]
        self.assertTrue(r0.get('success'), r0)
        self.assertEqual(r0.get('projectId'), pid)
        self.assertEqual(int(r0['project'].get('progress') or 0), 10)
        self.assertEqual(r0['event']['id'], 'act-smoke-001')

        # Idempotency: same action id returns existing event and current project.
        resp2 = self.client.post('/api/agent/actions', json=payload)
        self.assertEqual(resp2.status_code, 200, resp2.get_data(as_text=True))
        body2 = resp2.get_json()
        self.assertTrue(body2.get('success'), body2)
        r0b = body2['data']['results'][0]
        self.assertTrue(r0b.get('success'), r0b)
        self.assertEqual(r0b.get('message'), 'action exists')


if __name__ == '__main__':
    unittest.main(verbosity=2)
