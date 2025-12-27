from stores.models import Store
s=Store.objects.filter(id=1).first()
print(s and (s.latitude,s.longitude))
