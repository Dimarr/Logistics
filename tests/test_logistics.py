import datetime
import pytest
from graphene.test import Client
import django

django.setup()

from Logistics.schema import schema
from Logistics.models import Vehicle, DeliveryJob
from Logistics.auth import generate_jwt_token
from django.contrib.auth.models import User


@pytest.fixture
def graphql_client():
    return Client(schema)

'''
@pytest.fixture
def auth_token():
    user = User.objects.get(username='test')
    # Generate a JWT token for the user
    token = generate_jwt_token(user.id)
    return token
'''

@pytest.mark.django_db
def test_create_vehicle(graphql_client):
    # Test code for creating a vehicle
    mutation = '''
        mutation CreateVehicle($make: String!, $model: String!, $year: Int!) {
            createVehicle(make: $make, model: $model, year: $year) {
                vehicle {
                    id
                    make
                    model
                    year
                    isActive
                }
            }
        }
    '''
    variables = {'make': 'Toyota', 'model': 'Camry', 'year': 2022}
    response = graphql_client.execute(mutation, variables=variables)
    assert 'errors' not in response


@pytest.mark.django_db
def test_create_delivery_job(graphql_client):
    # Test code for creating a delivery job
    mutation = '''
        mutation CreateDeliveryJob($destination_location: String!, $delivery_slot: DateTime!, $income: Decimal!, $costs: Decimal!, $vehicle_id: ID!) {
            createDeliveryJob(destinationLocation: $destination_location, deliverySlot: $delivery_slot, income: $income, costs: $costs, vehicleId: $vehicle_id) {
                deliveryJob {
                    id
                    destinationLocation
                    deliverySlot
                    income
                    costs
                    vehicle {
                        id
                        make
                        model
                        year
                        isActive
                    }
                }
            }
        }
    '''
    variables = {
        'destination_location': 'My Location',
        'delivery_slot': datetime.datetime.now().isoformat(),
        'income': 100.50,
        'costs': 50.25,
        'vehicle_id': '1'
    }
    response = graphql_client.execute(mutation, variables=variables)
    assert 'errors' not in response


@pytest.mark.django_db
def test_get_count():
    # Test code for getting count of delivery jobs
    count = DeliveryJob.objects.count()
    assert isinstance(count, int)


@pytest.mark.django_db
def test_get_all_delivery_jobs_with_filter():
    # Test code for getting all delivery jobs with a filter
    queryset = DeliveryJob.objects.filter(destination_location='My Location')
    assert queryset.exists()


@pytest.mark.django_db
def test_calculate_monthly_income_costs(graphql_client):
    query = '''
        query CalculateMonthlyIncomeCosts($month: Int) {
            calculateMonthlyIncomeCosts(month: $month) {
                totalIncome
                totalCosts
            }
        }
    '''
    variables = {'month': 2}  # Assuming February is represented by month number 2
    response = graphql_client.execute(query, variables=variables)
    data = response.get('data', {})

    assert 'calculateMonthlyIncomeCosts' in data
    assert 'totalIncome' in data['calculateMonthlyIncomeCosts']
    assert 'totalCosts' in data['calculateMonthlyIncomeCosts']


@pytest.mark.django_db
def test_assign_vehicle_to_job(graphql_client):
    delivery_job = DeliveryJob.objects.create(
        created_at=datetime.datetime.now(),
        destination_location='Test Location',
        delivery_slot=datetime.datetime.now(),
        income=100.0,
        costs=50.0
    )
    vehicle = Vehicle.objects.create(
        make='Test Make',
        model='Test Model',
        year=2022,
        is_active=True
    )
    # Prepare the GraphQL mutation query
    mutation = '''
        mutation AssignVehicleToJob($jobId: ID!, $vehicleId: ID!) {
            assignVehicleToJob(jobId: $jobId, vehicleId: $vehicleId) {
                deliveryJob {
                    id
                    vehicle {
                        id
                    }
                }
            }
        }
    '''

    # Set the variables for the mutation query
    variables = {'jobId': str(delivery_job.id), 'vehicleId': str(vehicle.id)}

    # Execute the mutation query
    response = graphql_client.execute(mutation, variables=variables)
    data = response.get('data', {})

    # Check if the vehicle has been assigned to the delivery job
    assert 'assignVehicleToJob' in data
    assert data['assignVehicleToJob']['deliveryJob']['id'] == str(delivery_job.id)
    assert data['assignVehicleToJob']['deliveryJob']['vehicle']['id'] == str(vehicle.id)

    # Refresh the delivery job instance from the database to ensure it reflects the changes
    delivery_job.refresh_from_db()
    assert delivery_job.vehicle == vehicle


@pytest.mark.django_db
def test_mark_delivery_jobs_as_completed(graphql_client):
    delivery_job = DeliveryJob.objects.create(
        created_at=datetime.datetime.now(),
        destination_location='Test Location',
        delivery_slot=datetime.datetime.now(),
        income=100.0,
        costs=50.0
    )
    # Prepare the GraphQL mutation query
    mutation = '''
        mutation MarkDeliveryJobsAsCompleted($jobIds: [Int!]!) {
            markDeliveryJobsAsCompleted(jobIds: $jobIds) {
                success
                msg
            }
        }
    '''

    # Set the variables for the mutation query
    variables = {'jobIds': [delivery_job.id]}

    # Execute the mutation query
    response = graphql_client.execute(mutation, variables=variables)
    data = response.get('data', {})

    # Check if the delivery job was marked as completed successfully
    assert 'markDeliveryJobsAsCompleted' in data
    assert data['markDeliveryJobsAsCompleted']['success'] is True

    # Refresh the delivery job instance from the database to ensure it reflects the changes
    delivery_job.refresh_from_db()
    assert delivery_job.completed_at is not None
    assert delivery_job.completed_at.date() == datetime.datetime.now().date()


@pytest.mark.django_db
def test_order_by_most_profitable_vehicle(graphql_client):
    vehicle1 = Vehicle.objects.create(make='Vehicle 1 Make', model='Vehicle 1 Model', year=2022, is_active=True)
    vehicle2 = Vehicle.objects.create(make='Vehicle 2 Make', model='Vehicle 2 Model', year=2022, is_active=True)

    DeliveryJob.objects.create(destination_location='Location 1', income=1200, costs=50, vehicle=vehicle1)
    DeliveryJob.objects.create(destination_location='Location 2', income=1300, costs=100, vehicle=vehicle1)
    DeliveryJob.objects.create(destination_location='Location 3', income=1400, costs=150, vehicle=vehicle2)
    DeliveryJob.objects.create(destination_location='Location 4', income=1500, costs=200, vehicle=vehicle2)

    # Prepare the GraphQL query to retrieve delivery jobs ordered by the most profitable vehicle
    query = '''
        query {
            allDeliveryJobs(orderByMostProfitableVehicle: true) {
                id
                destinationLocation
                income
                costs
                vehicle {
                    id
                    make
                    model
                }
            }
        }
    '''

    # Execute the GraphQL query
    response = graphql_client.execute(query)
    data = response.get('data', {})

    # Extract the delivery jobs from the response
    delivery_jobs = data.get('allDeliveryJobs', [])

    # Assuming the delivery jobs are ordered by the most profitable vehicle, assert the order
    assert delivery_jobs[0]['vehicle']['id'] == str(vehicle2.id)
    assert delivery_jobs[1]['vehicle']['id'] == str(vehicle2.id)
    assert delivery_jobs[2]['vehicle']['id'] == str(vehicle1.id)
    assert delivery_jobs[3]['vehicle']['id'] == str(vehicle1.id)
