from django.urls import path
from .views import (
    CategoryListView, MasterListView, MasterDetailView,
    MasterRateView, MasterMyProfileView, SearchSuggestionsView,
    LocationsListView, FavoriteToggleView, FavoriteListView, MyRatingsListView,
    PortfolioListCreateView, PortfolioDeleteView
)

urlpatterns = [
    path('categories/', CategoryListView.as_view(), name='category-list'),
    path('masters/', MasterListView.as_view(), name='master-list'),
    path('masters/<int:pk>/', MasterDetailView.as_view(), name='master-detail'),
    path('masters/<int:pk>/rate/', MasterRateView.as_view(), name='master-rate'),
    path('masters/me/', MasterMyProfileView.as_view(), name='master-my-profile'),
    path('masters/me/portfolio/', PortfolioListCreateView.as_view(), name='master-portfolio-list-create'),
    path('masters/me/portfolio/<int:pk>/', PortfolioDeleteView.as_view(), name='master-portfolio-delete'),
    path('search/suggestions/', SearchSuggestionsView.as_view(), name='search-suggestions'),
    path('locations/', LocationsListView.as_view(), name='locations-list'),
    path('favorites/', FavoriteListView.as_view(), name='favorite-list'),
    path('favorites/toggle/<int:master_id>/', FavoriteToggleView.as_view(), name='favorite-toggle'),
    path('ratings/my/', MyRatingsListView.as_view(), name='my-ratings-list'),
]
