from django.utils import timezone
from users.models import User, LivreurProfile

ids = [5,7]
for uid in ids:
    try:
        u = User.objects.get(id=uid)
        try:
            p = LivreurProfile.objects.get(user=u)
            p.documents_verifies = True
            p.position_lat = 0.416200
            p.position_lng = 9.467300
            p.last_position_update = timezone.now()
            p.save()
            print('UPDATED profile for', u.id, u.phone)
        except LivreurProfile.DoesNotExist:
            print('No LivreurProfile for', uid)
    except User.DoesNotExist:
        print('No user', uid)
