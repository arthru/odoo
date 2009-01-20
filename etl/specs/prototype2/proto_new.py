#csv_in ---> logger
import csv
import sys
import time

class component(object):
    is_end = False
    def __init__(self,*args, **argv):
        self.trans_in = []
        self.trans_out = []
        self.is_output = False
        self.data = {}
        self.generator = None

    def generator_get(self, transition):
        if self.generator:
            return self.generator
        self.generator = self.process()
        return self.generator

    def channel_get(self, trans=None):
        self.data.setdefault(trans, [])
        gen = self.generator_get(trans) or []
        while True:
            if self.data[trans]:
                yield self.data[trans].pop(0)
                continue
            elif self.data[trans] is None:
                raise StopIteration
            data, chan = gen.next()
            if data is None:
                raise StopIteration
            for t,t2 in self.trans_out:
                if (t == chan) or (not t) or (not chan):
                    self.data.setdefault(t2, [])
                    self.data[t2].append(data)

    def process(self):
        pass

    def input_get(self):
        result = {}
        for channel,trans in self.trans_in:
            result.setdefault(channel, [])
            result[channel].append(trans.source.channel_get(trans))
        return result

class csv_in(component):
    def __init__(self, filename, *args, **argv):
        super(csv_in, self).__init__(*args, **argv)
        self.filename = filename

    def process(self):
        fp = csv.DictReader(file(self.filename))            
        for row in fp:
            yield row, 'main'

class csv_out(component):
    def __init__(self, filename, *args, **argv):
        super(csv_out, self).__init__(*args, **argv)
        self.filename=filename
        self.fp=None        

    def process(self):
        datas = []
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:
                    datas.append(d)
        self.fp=file(self.filename, 'wb+') 
        fieldnames = datas[0].keys()
        fp = csv.DictWriter(self.fp, fieldnames)
        fp.writerow(dict(map(lambda x: (x,x), fieldnames)))
        fp.writerows(datas)
        for d in datas:
            yield d, 'main'

class sort(component):
    def __init__(self, fieldname, *args, **argv):
        super(sort, self).__init__(*args, **argv)
        self.fieldname = fieldname

    # Read all input channels, sort and write to 'main' channel
    def process(self):
        datas = []                
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:
                    datas.append(d)
        
        datas.sort(lambda x,y: cmp(x[self.fieldname],y[self.fieldname]))
        for d in datas:
            yield d, 'main'

class logger_bloc(component):
    def __init__(self, name, output=sys.stdout, *args, **argv):
        self.name = name
        self.output = output
        self.is_end = 'main'
        super(logger, self).__init__(*args, **argv) 

    def process(self): 
        datas=[]
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:
                    datas.append(d)
        for d in datas:
            self.output.write('\tBloc Log '+self.name+str(d)+'\n')
            yield d, 'main'


class sleep(component):
    def __init__(self, delay=1, *args, **argv):
        self.delay = delay
        super(sleep, self).__init__(*args, **argv) 

    def process(self): 
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:
                    time.sleep(self.delay)
                    yield d, 'main'

class logger(component):
    def __init__(self, name, output=sys.stdout, *args, **argv):
        self.name = name
        self.output = output
        self.is_end = 'main'
        super(logger, self).__init__(*args, **argv) 

    def process(self): 
        for channel,trans in self.input_get().items():
            for iterator in trans:
                for d in iterator:
                    self.output.write('\tLog '+self.name+str(d)+'\n')
                    yield d, 'main'

class transition(object):
    def __init__(self, source, destination,type='data_transition', status='open', channel_source='main', channel_destination='main'):
        self.type=type
        self.source = source
        self.destination = destination
        self.channel_source = channel_source
        self.channel_destination = channel_destination
        self.destination.trans_in.append((channel_destination,self)) #:source.channel_get(self)})
        self.source.trans_out.append((channel_source,self))

class job(object):
    def __init__(self,outputs=[]):
        self.outputs=outputs

    def run(self):
        for c in self.outputs:
            for a in c.channel_get():
                pass

csv_in1= csv_in('partner.csv')
csv_in2= csv_in('partner1.csv')
csv_out1= csv_out('partner2.csv')
sort1=sort('name')
log1=logger(name='Read Partner File')
log2=logger(name='After Sort')
sleep1=sleep(1)

tran=transition(csv_in1,sort1)
tran1=transition(csv_in2,sort1)
tran4=transition(sort1,sleep1)
tran4=transition(sleep1,log2)
tran5=transition(sort1,csv_out1)


job1=job([csv_out1,log2])
job1.run()

# this is not work, log2 can not get data

#job2=job([log1,sort1,csv_out1,log2]) 
#job2.run(0)

