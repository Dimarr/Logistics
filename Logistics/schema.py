import graphene
import json
from django.core.paginator import Paginator, EmptyPage
from graphene_django.types import DjangoObjectType
from django.db.models import Sum, F, ExpressionWrapper, DecimalField
from graphene import JSONString
from .models import Vehicle, DeliveryJob
from datetime import datetime
from decimal import Decimal


class VehicleType(DjangoObjectType):
    class Meta:
        model = Vehicle
        fields = ("id", "make", "model", "year", "is_active")


class DeliveryJobType(DjangoObjectType):
    class Meta:
        model = DeliveryJob
        fields = ("id", "created_at", "destination_location", "delivery_slot", "income", "costs", "completed_at", "vehicle")


class MonthlyIncomeCosts(graphene.ObjectType):
    total_income = graphene.Float()
    total_costs = graphene.Float()


class Query(graphene.ObjectType):
    calculate_monthly_income_costs = graphene.Field(MonthlyIncomeCosts, month=graphene.Int())

    all_vehicles = graphene.List(
        VehicleType,
        make=graphene.String(),
        model=graphene.String(),
        year=graphene.Int(),
        is_active=graphene.Boolean(),
        page=graphene.Int(),
        page_size=graphene.Int(),
    )
    all_delivery_jobs = graphene.List(
        DeliveryJobType,
        destination_location=graphene.String(),
        delivery_slot=graphene.DateTime(),
        income=graphene.Decimal(),
        costs=graphene.Decimal(),
        vehicle_id=graphene.ID(),
        num_rows=graphene.Int(),
        page=graphene.Int(),
        page_size=graphene.Int(),
        orderByMostProfitableVehicle=graphene.Boolean()
    )
    delivery_jobs_count = graphene.Int(
        destination_location=graphene.String(),
        delivery_slot=graphene.DateTime(),
        income=graphene.Decimal(),
        costs=graphene.Decimal(),
        vehicle_id=graphene.ID()
    )

    def resolve_calculate_monthly_income_costs(root, info, month=None):
        # Get the current month if month is not provided
        if month is None:
            month = datetime.now().month

        # Calculate the sum of incomes and costs for the given month
        total_income = DeliveryJob.objects.filter(delivery_slot__month=month).aggregate(total_income=Sum('income'))[
                           'total_income'] or Decimal(0)
        total_costs = DeliveryJob.objects.filter(delivery_slot__month=month).aggregate(total_costs=Sum('costs'))[
                          'total_costs'] or Decimal(0)

        # Return both total income and total costs
        return MonthlyIncomeCosts(total_income=total_income, total_costs=total_costs)

    def resolve_all_vehicles(root, info, **kwargs):
        queryset = Vehicle.objects.all()
        page = kwargs.get('page')
        page_size = kwargs.get('page_size')
        page = 1 if not page else page
        page_size = 10 if not page_size else page_size
        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return page_obj.object_list

    def resolve_delivery_jobs_count(root, info, **kwargs):
        destination_location = kwargs.get('destination_location')
        delivery_slot = kwargs.get('delivery_slot')
        income = kwargs.get('income')
        costs = kwargs.get('costs')
        vehicle_id = kwargs.get('vehicle_id')
        queryset = DeliveryJob.objects.all()
        filters = {}
        if destination_location:
            filters['destination_location'] = destination_location
        if delivery_slot:
            filters['delivery_slot'] = delivery_slot
        if income:
            filters['income'] = income
        if costs:
            filters['costs'] = costs
        if vehicle_id:
            filters['vehicle_id'] = vehicle_id
        if filters:
            queryset = queryset.filter(**filters)
        return queryset.count()

    def resolve_all_delivery_jobs(root, info, **kwargs):
        destination_location = kwargs.get('destination_location')
        delivery_slot = kwargs.get('delivery_slot')
        income = kwargs.get('income')
        costs = kwargs.get('costs')
        vehicle_id = kwargs.get('vehicle_id')
        order_by_most_profitable_vehicle = kwargs.get('orderByMostProfitableVehicle') == True
        page = kwargs.get('page')
        page_size = kwargs.get('page_size')
        page = 1 if not page else page
        page_size = 10 if not page_size else page_size

        queryset = DeliveryJob.objects.all()
        filters = {}
        if destination_location:
            filters['destination_location'] = destination_location
        if delivery_slot:
            filters['delivery_slot'] = delivery_slot
        if income:
            filters['income'] = income
        if costs:
            filters['costs'] = costs
        if vehicle_id:
            filters['vehicle_id'] = vehicle_id
        if filters:
            queryset = queryset.filter(**filters)

        if order_by_most_profitable_vehicle:
            # Calculate the profit (income - costs) for each vehicle
            queryset = queryset.annotate(
                profit=ExpressionWrapper(F('income') - F('costs'), output_field=DecimalField()))
            queryset = queryset.values('vehicle').annotate(total_profit=Sum('profit')).order_by('-total_profit')
            most_profitable_vehicle_ids = queryset.values_list('vehicle_id', flat=True)
            # Perform a query to fetch delivery jobs sorted by the profit generated by each vehicle
            queryset = DeliveryJob.objects.filter(vehicle__in=most_profitable_vehicle_ids)

        paginator = Paginator(queryset, page_size)
        try:
            page_obj = paginator.page(page)
        except EmptyPage:
            page_obj = paginator.page(paginator.num_pages)
        return page_obj.object_list


class CreateVehicle(graphene.Mutation):
    class Arguments:
        make = graphene.String()
        model = graphene.String()
        year = graphene.Int()

    vehicle_data = JSONString()
    vehicle = graphene.Field(VehicleType)

    @staticmethod
    def mutate(root, info, make, model, year):
        vehicle = Vehicle(make=make, model=model, year=year)
        vehicle.save()

        vehicle_data = {
            "id": vehicle.id,
            "make": vehicle.make,
            "model": vehicle.model,
            "year": vehicle.year,
            "is_active": vehicle.is_active,
        }
        # Return the data of the created vehicle in JSON format
        return CreateVehicle(vehicle=vehicle, vehicle_data=json.dumps(vehicle_data))


class CreateDeliveryJob(graphene.Mutation):
    class Arguments:
        destination_location = graphene.String()
        delivery_slot = graphene.DateTime()
        income = graphene.Decimal()
        costs = graphene.Decimal()
        vehicle_id = graphene.ID()

    delivery_job = graphene.Field(DeliveryJobType)
    delivery_job_data = JSONString()

    @staticmethod
    def mutate(root, info, destination_location, delivery_slot, income, costs, vehicle_id):
        vehicle = Vehicle.objects.get(pk=vehicle_id)
        delivery_job = DeliveryJob(destination_location=destination_location, delivery_slot=delivery_slot, income=income, costs=costs, vehicle=vehicle)
        delivery_job.save()
        delivery_job_data = {
            "id": delivery_job.id,
            "destination_location": delivery_job.destination_location,
            "delivery_slot": delivery_job.delivery_slot.isoformat(),
            "income": float(delivery_job.income),
            "costs": float(delivery_job.costs),
        }
        return CreateDeliveryJob(delivery_job = delivery_job, delivery_job_data=delivery_job_data)


class AssignVehicleToJob(graphene.Mutation):
    class Arguments:
        job_id = graphene.ID(required=True)
        vehicle_id = graphene.ID(required=True)

    delivery_job = graphene.Field(DeliveryJobType)

    @staticmethod
    def mutate(root, info, job_id, vehicle_id):
        # Get the delivery job and vehicle objects
        job = DeliveryJob.objects.get(pk=job_id)
        vehicle = Vehicle.objects.get(pk=vehicle_id)

        # Assign the vehicle to the job
        job.vehicle = vehicle
        job.save()

        return AssignVehicleToJob(delivery_job=job)


class MarkDeliveryJobsAsCompleted(graphene.Mutation):
    class Arguments:
        job_ids = graphene.List(graphene.Int, required=True)

    success = graphene.Boolean()
    msg = graphene.String()

    @staticmethod
    def mutate(root, info, job_ids):
        try:
            # Update the DeliveryJob objects with the given IDs to mark them as completed
            delivery_jobs = DeliveryJob.objects.filter(id__in=job_ids)
            if delivery_jobs.count() > 0:
                delivery_jobs.update(completed_at=datetime.now())  # Set completed_at to current datetime
                success = True
                msg = "Nice"
            else:
                msg=f"{job_ids} does not exist"
                success = False
        except Exception as e:
            print(e)
            success = False

        return MarkDeliveryJobsAsCompleted(success=success, msg=msg)


class Mutation(graphene.ObjectType):
    create_vehicle = CreateVehicle.Field()
    create_delivery_job = CreateDeliveryJob.Field()
    assign_vehicle_to_job = AssignVehicleToJob.Field()
    mark_delivery_jobs_as_completed = MarkDeliveryJobsAsCompleted.Field()

schema = graphene.Schema(query=Query, mutation=Mutation)