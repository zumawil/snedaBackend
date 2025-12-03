"""
Base generic views that automatically use api_response utility.
This ensures all generic views return consistent response format.
"""

from rest_framework import generics, status
from .apiResponse import api_response


class GenericListCreateAPIView(generics.ListCreateAPIView):
    """
    Base ListCreateAPIView that uses api_response for all responses.
    """
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message=f"{self.get_serializer().Meta.model.__name__}s retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                success=True,
                data=serializer.data,
                message=f"{self.get_serializer().Meta.model.__name__} created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        # Use normalized errors for better readability
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,  # This will be normalized by api_response
            status_code=status.HTTP_400_BAD_REQUEST
        )


class GenericRetrieveUpdateDestroyAPIView(generics.RetrieveUpdateDestroyAPIView):
    """
    Base RetrieveUpdateDestroyAPIView that uses api_response for all responses.
    """
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message=f"{self.get_serializer().Meta.model.__name__} retrieved successfully",
            status_code=status.HTTP_200_OK
        )
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message=f"{self.get_serializer().Meta.model.__name__} updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message=f"{self.get_serializer().Meta.model.__name__} deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )


class GenericListAPIView(generics.ListAPIView):
    """
    Base ListAPIView that uses api_response for all responses.
    """
    
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return api_response(
            success=True,
            data=serializer.data,
            message=f"{self.get_serializer().Meta.model.__name__}s retrieved successfully",
            status_code=status.HTTP_200_OK
        )


class GenericRetrieveAPIView(generics.RetrieveAPIView):
    """
    Base RetrieveAPIView that uses api_response for all responses.
    """
    
    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        return api_response(
            success=True,
            data=serializer.data,
            message=f"{self.get_serializer().Meta.model.__name__} retrieved successfully",
            status_code=status.HTTP_200_OK
        )


class GenericCreateAPIView(generics.CreateAPIView):
    """
    Base CreateAPIView that uses api_response for all responses.
    """
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        if serializer.is_valid():
            self.perform_create(serializer)
            return api_response(
                success=True,
                data=serializer.data,
                message=f"{self.get_serializer().Meta.model.__name__} created successfully",
                status_code=status.HTTP_201_CREATED
            )
        
        # Use normalized errors for better readability
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,  # This will be normalized by api_response
            status_code=status.HTTP_400_BAD_REQUEST
        )


class GenericUpdateAPIView(generics.UpdateAPIView):
    """
    Base UpdateAPIView that uses api_response for all responses.
    """
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        if serializer.is_valid():
            serializer.save()
            return api_response(
                success=True,
                data=serializer.data,
                message=f"{self.get_serializer().Meta.model.__name__} updated successfully",
                status_code=status.HTTP_200_OK
            )
        return api_response(
            success=False,
            data=None,
            error="Validation failed",
            message=serializer.errors,
            status_code=status.HTTP_400_BAD_REQUEST
        )


class GenericDestroyAPIView(generics.DestroyAPIView):
    """
    Base DestroyAPIView that uses api_response for all responses.
    """
    
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        instance.delete()
        return api_response(
            success=True,
            data=None,
            message=f"{self.get_serializer().Meta.model.__name__} deleted successfully",
            status_code=status.HTTP_204_NO_CONTENT
        )