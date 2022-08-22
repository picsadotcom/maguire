import os
from django.conf.urls import include, url
from django.contrib import admin
from django.views.decorators.csrf import csrf_exempt
from django.contrib.admin.views.decorators import staff_member_required
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import authentication_classes, permission_classes, api_view
from graphene_django.views import GraphQLView
from maguire.schema import schema
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = os.environ.get('MAGUIRE_TITLE', 'Maguire Admin')


def graphql_token_view():
    view = GraphQLView.as_view(schema=schema)
    view = permission_classes((IsAuthenticated,))(view)
    view = authentication_classes((TokenAuthentication,))(view)
    view = api_view(['POST'])(view)
    return view


urlpatterns = [
    url(r'^admin/doc/', include('django.contrib.admindocs.urls')),
    url(r'^admin/', admin.site.urls),
    url(r'^graphql', graphql_token_view()),
    url(r'^graphiql', staff_member_required(csrf_exempt(
        GraphQLView.as_view(schema=schema, graphiql=True)))),
    url(r'^api/rest-auth/', include('rest_auth.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
