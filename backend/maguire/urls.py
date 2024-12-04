import os

from django.conf import settings
from django.conf.urls import include
from django.conf.urls.static import static
from django.contrib import admin
from django.contrib.admin.views.decorators import staff_member_required
from django.urls import re_path
from django.views.decorators.csrf import csrf_exempt

from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes, api_view

from graphene_django.views import GraphQLView

from maguire.schema import schema

admin.site.site_header = os.environ.get('MAGUIRE_TITLE', 'Maguire Admin')


def graphql_token_view():
    view = GraphQLView.as_view(schema=schema)
    view = permission_classes((IsAuthenticated,))(view)
    view = authentication_classes((TokenAuthentication,))(view)
    view = api_view(['POST'])(view)
    return view


urlpatterns = [
    re_path(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    re_path(r'^admin/', admin.site.urls),
    re_path(r'^graphql', graphql_token_view()),
    re_path(r'^graphiql', staff_member_required(csrf_exempt(
        GraphQLView.as_view(schema=schema, graphiql=True)))),
    re_path(r'^api/rest-auth/', include('dj_rest_auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
