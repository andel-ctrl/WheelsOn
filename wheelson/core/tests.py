from django.test import TestCase, Client

class WheelsOnSetupTest(TestCase):
    def setUp(self):
        self.client = Client()

    def test_dashboard_renders(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'WheelsOn')
        self.assertContains(response, 'Red Profesional Orientada a Grafos')
        self.assertContains(response, 'Neo4j')
