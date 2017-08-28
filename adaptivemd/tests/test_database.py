import os
import json
import random
import string
import unittest
from adaptivemd.rp.database import Database

# Configuration Variables
mongo_url = 'mongodb://user:user@two.radical-project.org:32769/'
project = 'rp_testing'

# Example JSON locations
directory = os.path.dirname(os.path.abspath(__file__))
conf_example = 'example-json/configuration-example.json'
res_example = 'example-json/resource-example.json'
task_example = 'example-json/task-example.json'
file_example = 'example-json/file-example.json'
gen_example = 'example-json/generator-example.json'


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    """Random ID/String Generator"""
    return ''.join(random.choice(chars) for _ in range(size))


class TestDatabase(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        """Initialize tests, just creates instance variables needed and the DB object.
        """
        super(TestDatabase, cls).setUpClass()
        cls.db = Database(mongo_url=mongo_url,
                          project='{}_{}'.format(project, id_generator()))

        # Create Database and collections
        client = cls.db.client
        cls.store_name = "{}-{}".format(cls.db.store_prefix, cls.db.project)
        mongo_db = client[cls.store_name]
        tasks_col = mongo_db[cls.db.tasks_collection]
        configs_col = mongo_db[cls.db.configuration_collection]
        resources_col = mongo_db[cls.db.resource_collection]
        files_col = mongo_db[cls.db.file_collection]
        generators_col = mongo_db[cls.db.generator_collection]

        # Insert test documents
        with open('{}/{}'.format(directory, conf_example)) as json_data:
            data = json.load(json_data)
            configs_col.insert_one(data)

        with open('{}/{}'.format(directory, res_example)) as json_data:
            data = json.load(json_data)
            resources_col.insert_one(data)

        with open('{}/{}'.format(directory, file_example)) as json_data:
            data = json.load(json_data)
            for file_entry in data:
                files_col.insert_one(file_entry)

        with open('{}/{}'.format(directory, gen_example)) as json_data:
            data = json.load(json_data)
            generators_col.insert_one(data)

        with open('{}/{}'.format(directory, task_example)) as json_data:
            # insert tasks
            data = json.load(json_data)
            for task_entry in data:
                tasks_col.insert_one(task_entry)

    @classmethod
    def tearDownClass(cls):
        """Destroy the database since we don't need it anymore"""
        client = cls.db.client
        client.drop_database(cls.store_name)
        client.close()

    def test_task_descriptions(self):
        """Test that the task descriptions method returns a list
        and that the list is of size '2'"""
        task_descriptions = self.db.get_task_descriptions()
        self.assertEquals(type(task_descriptions), list)
        self.assertEquals(len(task_descriptions), 2)

    def test_resource_requirements(self):
        """Test that the resource requirements method returns a list
        and that the list is of size '1'"""
        resource_requirements = self.db.get_resource_requirements()
        self.assertEquals(type(resource_requirements), list)
        self.assertEquals(len(resource_requirements), 1)

    def test_configurations(self):
        """Test that the configurations method returns a list
        and that the list is of size '1'"""
        configurations = self.db.get_configurations()
        self.assertEquals(type(configurations), list)
        self.assertEquals(len(configurations), 1)

    def test_get_file_destination(self):
        """Test that the proper location is returned"""
        location = self.db.get_file_destination(
            id='1126d076-8b9e-11e7-b37f-000000000006')
        self.assertEquals(
            location,
            "file:///home/vivek/ves/admd/local/lib/python2.7/" +
            "site-packages/adaptivemd/engine/openmm/openmmrun.py")

    def test_get_source_files(self):
        """Test that the proper location list is returned"""
        locations = self.db.get_source_files(
            id='1126d076-8b9e-11e7-b37f-000000000044')
        self.assertTrue(
            all(
                any(
                    x in y for y in locations
                ) for x in ['master.dcd', 'protein.dcd']
            )
        )

    def test_get_shared_files(self):
        """Test that the proper shared location list is returned"""
        locations = self.db.get_shared_files()
        expected_data = [
            'file:///home/vivek/ves/admd/local/lib/python2.7/' +
            'site-packages/adaptivemd/engine/openmm/openmmrun.py',
            'file:///home/vivek/Research/repos/adaptivemd/' +
            'examples/files/alanine/alanine.pdb',
            'file:///home/vivek/Research/repos/adaptivemd/' +
            'examples/files/alanine/integrator.xml',
            'file:///home/vivek/Research/repos/adaptivemd/' +
            'examples/files/alanine/system.xml'
        ]
        self.assertTrue(
            all(
                any(
                    x in y for y in locations
                ) for x in expected_data
            )
        )

    def test_good_update_task_state(self):
        """Test that the task update state method returns
        true for a good update"""
        task_descriptions = self.db.get_task_descriptions()
        task = task_descriptions[0]
        self.assertTrue(self.db.update_task_description_status(
            id=task['_id'], state='fail'))
        self.db.update_task_description_status(
            id=task['_id'], state='created')

    def test_bad_update_task_state(self):
        """Test that the task update state method returns
        false for a bad update"""
        task_descriptions = self.db.get_task_descriptions()
        task = task_descriptions[0]
        self.assertFalse(self.db.update_task_description_status(
            id='{}_asdasd'.format(task['_id']), state='fail'))


if __name__ == '__main__':
    suite = unittest.TestLoader().loadTestsFromTestCase(TestDatabase)
    unittest.TextTestRunner(verbosity=2).run(suite)