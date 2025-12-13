"""
Exceptions partagées pour le module core
"""

class BusinessValidationError(Exception):
	"""Erreur levée pour des validations métier (utilisée dans validators)."""
	pass


class NotFoundError(Exception):
	"""Erreur levée lorsqu'une ressource métier est introuvable."""
	pass


class CoreError(Exception):
	"""Base pour les erreurs du module core."""
	pass
