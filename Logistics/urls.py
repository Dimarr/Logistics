from django.urls import path
from graphene_django.views import GraphQLView
from .auth import login

urlpatterns = [
    path('graphql/', GraphQLView.as_view(graphiql=True)),
    path('login/', login, name='login')
]
