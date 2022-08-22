import debits.schema
import graphene


class Query(
  debits.schema.Query,
  graphene.ObjectType):
    pass


class Mutation(
  debits.schema.Mutation,
  graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation)
